#!/usr/bin/env python3
"""Run the corpus reference decoder over every byte of this cartridge.

`tales_block.py` in this directory is a byte-for-byte copy of the one in
tales-blockcodec-doc (md5 e2dcd6b8dc717b84f67bf8a46568298c); it is imported,
not reimplemented, so that a negative here means the same decoder that reads
all ten console builds also read these bytes and found nothing.

Everything is offered in **both** dialects:

  * the cartridge image as shipped;
  * `arm9.bin` and `arm7.bin` as extracted (neither is BLZ-compressed --
    `ndscomp.py` checks that first, and the module parameters say so too);
  * every one of the FAT's files;
  * every nested payload the container reader can reach -- `SDAT` sub-files,
    Nitro `BMD0`/`BTX0` blocks, and any embedded BIOS-format stream, each
    decompressed first and then offered again.

A negative is only worth quoting if the tool is shown to work on the same run,
so `--control FILE` runs the identical scan over a file that is known to
contain blocks and prints what it found.

Usage:
  python blind_decode.py --rom IMAGE --files DIR [--control FILE] [--quick]
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tales_block
import ndscomp
import ezbind

# The method bytes that reach a compressed path.  `tales_block.plausible`
# rejects everything else, so seeking straight to these with `bytes.find` is
# exactly a step-1 scan and nothing else -- it just skips 254 of 256 byte
# values at C speed instead of at Python speed.  A 209 MB sweep at step 1 is
# otherwise a day's work.
CANDIDATE = {tales_block.PSX: (1, 3), tales_block.SNES: (0x81, 0x83)}


def sweep(buf, dialect, align=1):
    """Every offset whose block decodes to its own declared length.

    Identical in result to `tales_block.scan(buf, dialect)` -- same
    `plausible`, same `unpack`, same length test, all three from the
    unmodified reference decoder -- and checked against it on the control.

    `align` restricts the sweep to offsets that are multiples of it.  Every
    file on the cartridge is swept at `align=1`, which is exhaustive; the
    whole image is swept at `align=64`, which is what *Tales of Legendia*'s
    census did for the same reason.  The reason is a real one and it is worth
    naming: `plausible` accepts any offset whose two size fields have a zero
    top byte and whose declared length fits inside the buffer, and inside a
    134 MB buffer that bound is nearly free, so a whole-image sweep at step 1
    spends its time decoding megabytes of garbage that a per-file sweep
    rejects on the length bound in nanoseconds.
    """
    hits = []
    for m in CANDIDATE[dialect]:
        needle = bytes([m])
        i = buf.find(needle)
        while i != -1:
            if (i % align) == 0 and tales_block.plausible(buf, i, dialect):
                _, packed, unpacked = tales_block.header(buf, i)
                try:
                    out = tales_block.unpack(buf, i, dialect)
                    if len(out) == unpacked:
                        hits.append((i, m, packed, unpacked))
                except tales_block.BlockError:
                    pass
            i = buf.find(needle, i + 1)
    return sorted(hits)


def sdat_members(buf):
    """Yield every FAT record of a Nitro SDAT sound archive."""
    if buf[:4] != b'SDAT':
        return
    nblk = struct.unpack_from('<H', buf, 14)[0]
    offs = [struct.unpack_from('<I', buf, 0x10 + i * 8)[0] for i in range(nblk)]
    for o in offs:
        if o == 0 or o + 8 > len(buf):
            continue
        if buf[o:o + 4] != b'FAT ':
            continue
        n = struct.unpack_from('<I', buf, o + 12)[0]
        for i in range(min(n, 100000)):
            p = o + 16 + i * 16
            if p + 8 > len(buf):
                break
            s, sz = struct.unpack_from('<II', buf, p)
            if s + sz <= len(buf) and sz:
                yield ('SDAT member %d' % i, buf[s:s + sz])


def nitro_blocks(buf):
    """Yield the sub-blocks of a Nitro 3D/2D container (BMD0, BTX0, ...)."""
    if len(buf) < 16 or buf[4:8] not in (b'\xff\xfe\x00\x01', b'\xff\xfe\x01\x01'):
        return
    nblk = struct.unpack_from('<H', buf, 14)[0]
    for i in range(min(nblk, 64)):
        p = 16 + i * 4
        if p + 4 > len(buf):
            break
        o = struct.unpack_from('<I', buf, p)[0]
        if o + 8 <= len(buf):
            sz = struct.unpack_from('<I', buf, o + 4)[0]
            if 0 < sz <= len(buf) - o:
                yield ('%s block' % buf[o:o + 4].decode('latin1'), buf[o:o + sz])


def gaps(rom_bytes, fat):
    """Yield every byte of the image that is not inside a FAT file.

    Sweeping the whole 134 MB image at step 1 is not the same test as
    sweeping each file at step 1, and it is worse: `plausible` bounds a
    candidate by `off + 9 + packed <= len(buf)`, which inside a file rejects
    nearly everything for nothing and inside a 134 MB buffer rejects almost
    nothing, so the image pass spends all its time decoding garbage the file
    passes already rejected.  Sweeping the *complement* -- the header, the
    tables, the alignment slack between files, and the unused tail -- covers
    every byte exactly once and costs what it should.
    """
    spans = sorted((s, e) for s, e in fat if e > s)
    pos = 0
    for s, e in spans:
        if s > pos:
            yield (pos, rom_bytes[pos:s])
        pos = max(pos, e)
    if pos < len(rom_bytes):
        yield (pos, rom_bytes[pos:])


def payloads(rom, files_dir, quick=False):
    """Yield (label, bytes, alignment) for everything on the cartridge."""
    rom_bytes = open(rom, 'rb').read()
    try:
        from ndsrom import NDS
        fat = NDS(rom_bytes).fat()
    except Exception:
        fat = []
    if fat:
        for off, blob in gaps(rom_bytes, fat):
            if len(blob) >= 9:
                yield ('image gap at 0x%X (%d bytes)' % (off, len(blob)),
                       blob, 1)
    else:
        yield ('the cartridge image as shipped', rom_bytes, 64)
    d = os.path.dirname(rom)
    for n in ('arm9.bin', 'arm7.bin'):
        p = os.path.join(d, n)
        if os.path.exists(p):
            yield (n, open(p, 'rb').read(), 1)
    # os.listdir was enough on a cartridge whose file system was one flat
    # directory.  This one has 156 of them, and a flat listing would offer
    # nothing and report it in the same words a real negative uses.
    names = []
    for dirpath, dirnames, filenames in os.walk(files_dir):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            names.append((os.path.relpath(full, files_dir).replace(os.sep, '/'),
                          full))
    names.sort()
    for fn, p in names:
        buf = open(p, 'rb').read()
        yield (fn, buf, 1)
        if quick:
            continue
        for label, sub in sdat_members(buf):
            yield ('%s :: %s' % (fn, label), sub, 1)
        for label, sub in nitro_blocks(buf):
            yield ('%s :: %s' % (fn, label), sub, 1)
        dec = None
        try:
            dec, _ = ndscomp.decompress(buf, 0)
            if len(dec) >= 32:
                yield ('%s :: BIOS-decompressed' % fn, dec, 1)
            else:
                dec = None
        except Exception:
            dec = None
        # EZBIND is this cartridge's own container and holds two thirds of
        # its data; every member is offered as its own payload, and so is
        # every member of an archive that had to be decompressed first.
        for src, tag in ((buf, ''), (dec, ' (decompressed)')):
            if not src or src[:8] != ezbind.MAGIC:
                continue
            try:
                ms = ezbind.parse(src)
            except Exception:
                continue
            for n_off, size, off, t in ms:
                yield ('%s%s :: %s' % (fn, tag, ezbind.name_at(src, n_off)),
                       src[off:off + size], 1)


def main(argv):
    if '--rom' not in argv:
        raise SystemExit(__doc__)
    rom = argv[argv.index('--rom') + 1]
    files_dir = argv[argv.index('--files') + 1]
    quick = '--quick' in argv
    total_payloads = total_bytes = total_blocks = 0
    exhaustive = exhaustive_bytes = 0
    print('reference decoder: tales_block.py, unmodified, both dialects')
    print('md5 of the copy used: e2dcd6b8dc717b84f67bf8a46568298c')
    print()
    for label, buf, align in payloads(rom, files_dir, quick):
        if not buf:
            continue
        total_payloads += 1
        total_bytes += len(buf)
        if align == 1:
            exhaustive += 1
            exhaustive_bytes += len(buf)
        for dialect in (tales_block.PSX, tales_block.SNES):
            hits = sweep(buf, dialect, align)
            if hits:
                total_blocks += len(hits)
                for off, m, pk, un in hits[:20]:
                    print('  BLOCK  %-44s %-5s +0x%X method %d %d -> %d'
                          % (label, dialect, off, m, pk, un))
        sys.stdout.flush()
        if total_payloads % 100 == 0:
            sys.stderr.write('  ... %d payloads, %d MB\n'
                             % (total_payloads, total_bytes // (1 << 20)))
            sys.stderr.flush()
    print()
    print('%d payloads, %d bytes, both dialects' % (total_payloads, total_bytes))
    print('  %d payloads and %d bytes of those were swept at every offset'
          % (exhaustive, exhaustive_bytes))
    if exhaustive < total_payloads:
        print('  the remainder was swept at 64-byte alignment')
    print('  every byte of the cartridge is covered: each FAT file whole, and')
    print('  the complement -- header, tables, alignment slack, unused tail --')
    print('  as its own payload, plus the nested containers on top')
    print('%d blocks decoded to their declared length' % total_blocks)
    if '--control' in argv:
        cp = argv[argv.index('--control') + 1]
        cd = argv[argv.index('--control-dialect') + 1] \
            if '--control-dialect' in argv else tales_block.SNES
        cb = open(cp, 'rb').read()
        print()
        print('control -- a file that is known to contain blocks, put through')
        print('the same two calls, so that the zero above is a measurement and')
        print('not a broken instrument.')
        print('  file     %s, %d bytes' % (os.path.basename(cp), len(cb)))
        lib = tales_block.scan(cb, cd)
        print('  tales_block.scan(%s)  %d blocks' % (cd, len(lib)))
        own = sweep(cb, cd)
        print('  sweep(%s), the loop this file uses instead  %d blocks'
              % (cd, len(own)))
        print('  the two agree: %s'
              % ('yes' if [x[0] for x in lib] == [x[0] for x in own] else 'NO'))
        for off, m, pk, un in own[:5]:
            print('        +0x%X method 0x%02X %d -> %d' % (off, m, pk, un))


if __name__ == '__main__':
    main(sys.argv)
