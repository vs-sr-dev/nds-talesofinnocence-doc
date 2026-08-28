#!/usr/bin/env python3
"""Classify every file on the cartridge, and account for every byte of it.

Classification is by **magic and arithmetic**, never by extension.  The
Nintendo containers announce themselves; the in-house formats mostly do not, so
each is identified by a size equation that either holds for every file of its
kind or does not, and the count is printed either way.

Written for *Tales of the Tempest*, which had no containers and four in-house
2D formats.  This cartridge has neither: what it has is 1,344 `EZBIND`
archives holding 9,646 members, a hundred of them behind a BIOS `LZ77` stream,
and CRI and Actimagine media instead of Nintendo's.  So the tool now does two
passes -- one over the files as the cartridge stores them, and one over the
members inside the containers, decompressing where it has to -- and prints
both, because attributing a container's bytes to its members' classes would
be an estimate where these two tables are measurements.

The Tempest formats are kept because the classifier is meant to be reusable:

    .nbm   u16 depth (0=4bpp, 1=8bpp, 2=16bpp direct), u16 width,
           u16 height, u16 zero, then pixels, then the palette
           -- size == 8 + w*h*depth_bytes + (32 | 512 | 0)
    .ANA   u16 tile count, u16 depth (0 = 4bpp, 1 = 8bpp), then 8x8 tiles
           -- size == 4 + tiles * (32 | 64)
    .APA   256 BGR555 entries -- size == 512, with no header at all
    .ASC   u16 width, u16 height in tiles, then u16 map entries
           -- size == 4 + w * h * 2

The budget is then the same measurement the rest of the corpus reports for a
disc, on a medium three orders of magnitude smaller.

    python formats.py IMAGE FILESDIR
    python formats.py IMAGE FILESDIR --csv   one row per file

Standard library only.
"""

import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ndsrom import NDS

MAGIC = {
    b'BMD0': ('3D model', 'Nitro NSBMD'),
    b'BTX0': ('3D texture', 'Nitro NSBTX'),
    b'BCA0': ('3D animation', 'Nitro NSBCA, joint'),
    b'BTA0': ('3D animation', 'Nitro NSBTA, texture SRT'),
    b'BMA0': ('3D animation', 'Nitro NSBMA, material'),
    b'BVA0': ('3D animation', 'Nitro NSBVA, visibility'),
    b'BTP0': ('3D animation', 'Nitro NSBTP, texture pattern'),
    b'SDAT': ('audio', 'Nitro sound archive'),
    b'VXDS': ('video', 'Actimagine VX'),
    b'<?xm': ('leftover', 'NITRO-System IMD, the exporter XML'),
    b'BM\x76\x08': ('leftover', 'Windows bitmap'),
    b'MODS': ('video', 'Actimagine Mobiclip'),
    b'RTFN': ('font', 'Nitro NFTR'),
    b'NARC': ('container', 'Nitro archive'),
    b'EZBI': ('container', 'in-house EZBIND'),
    b'Face': ('other', 'in-house FaceChat / FaceData'),
    b'DSpr': ('2D graphics', 'in-house DSpr sprite set'),
}

BIOS_TYPES = {0x10: 'LZ77', 0x11: 'LZ11', 0x24: 'Huffman4', 0x28: 'Huffman8',
              0x30: 'RLE', 0x81: 'Diff8', 0x82: 'Diff16'}


def cri(data):
    """CRI ADX / AHX, identified from the header rather than the extension.

    +0x00 u16 be 0x8000, +0x02 u16 be the offset of the stream, and the six
    bytes ending two before that offset read `(c)CRI`.  +0x04 is the format
    code: 3 is ADX ADPCM, 0x10 and 0x11 are AHX, which is MPEG-2 layer II.
    """
    if len(data) < 20 or data[0] != 0x80 or data[1] != 0x00:
        return None
    off = struct.unpack_from('>H', data, 2)[0]
    if off + 4 > len(data) or data[off - 2:off + 4] != b'(c)CRI':
        return None
    fmt = data[4]
    rate = struct.unpack_from('>I', data, 8)[0]
    samples = struct.unpack_from('>I', data, 12)[0]
    kind = {3: 'ADX ADPCM', 0x10: 'AHX', 0x11: 'AHX'}.get(fmt, 'code %d' % fmt)
    return ('audio', 'CRI %s, %d ch, %d Hz, %.2f s'
            % (kind, data[7], rate, samples / rate if rate else 0))


def classify(name, data):
    m4 = data[:4]
    if m4 == b'EZBI' and data[:8] != b'EZBIND' + bytes(2):
        m4 = None
    if m4 in MAGIC:
        return MAGIC[m4]
    c = cri(data)
    if c:
        return c
    if len(data) >= 4 and data[0] in BIOS_TYPES:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import ndscomp
            out, used = ndscomp.decompress(data, 0)
            if used == len(data) and len(out) > 16:
                cls, note = classify(name, out)
                return (cls, '%s, in a BIOS %s stream'
                        % (note, BIOS_TYPES[data[0]]))
        except Exception:
            pass
    if data[:2] == b'BM':
        return ('leftover', 'Windows bitmap')
    ext = name.rsplit('.', 1)[-1].lower()
    n = len(data)
    if ext in ('nbfc', 'ntft'):
        return ('2D graphics', 'Nitro basic format, character data')
    if ext in ('nbfp', 'ntfp'):
        return ('2D graphics', 'Nitro basic format, palette, %d entries' % (n // 2))
    if ext == 'nbfs':
        return ('2D graphics', 'Nitro basic format, screen map')
    if ext == 'txt':
        return ('text', 'plain text')
    if ext == 'scr':
        return ('other', 'in-house script')
    if ext == 'fdt':
        return ('other', 'in-house face data')
    if ext == 'nbm' and n >= 8:
        d, w, h, r = struct.unpack_from('<HHHH', data, 0)
        px = {0: w * h // 2, 1: w * h, 2: w * h * 2}.get(d)
        pal = {0: 32, 1: 512, 2: 0}.get(d)
        if px is not None and 8 + px + pal == n:
            return ('2D graphics', 'in-house bitmap, %dx%d %s'
                    % (w, h, {0: '4bpp', 1: '8bpp', 2: '16bpp direct'}[d]))
        return ('2D graphics', 'in-house bitmap, header does not fit the size')
    if ext == 'ana' and n >= 4:
        t, f = struct.unpack_from('<HH', data, 0)
        if 4 + t * 32 == n:
            return ('2D graphics', 'in-house tile set, %d tiles 4bpp%s'
                    % (t, '' if f == 0 else ' (depth word says %d)' % f))
        if 4 + t * 64 == n:
            return ('2D graphics', 'in-house tile set, %d tiles 8bpp%s'
                    % (t, '' if f == 1 else ' (depth word says %d)' % f))
        return ('2D graphics', 'in-house tile set, count does not fit the size')
    if ext == 'apa':
        return ('2D graphics', 'in-house palette, %d BGR555 entries' % (n // 2))
    if ext == 'asc' and n >= 4:
        w, h = struct.unpack_from('<HH', data, 0)
        if 4 + w * h * 2 == n:
            return ('2D graphics', 'in-house screen map, %dx%d tiles' % (w, h))
        return ('2D graphics', 'in-house screen map, size does not fit')
    if ext == 'mes':
        return ('text', 'in-house message file')
    if ext in ('vtx', 'srf', 'dat'):
        return ('geometry / collision', 'in-house %s' % ext)
    if ext == 'char':
        return ('2D graphics', 'in-house character data')
    if ext == 'plt':
        return ('2D graphics', 'in-house palette, %d entries' % (n // 2))
    if ext == 'bnr':
        return ('leftover', 'a second copy of the cartridge banner')
    if ext == 'bin':
        return ('other', 'unclassified')
    return ('other', 'unclassified')


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    rom = open(argv[1], 'rb').read()
    r = NDS(rom)
    files, dirs = r.fnt()
    fat = r.fat()
    root = argv[2]

    rows = []
    for fid, path in files:
        s, e = fat[fid]
        name = path.rsplit('/', 1)[-1]
        p = os.path.join(root, path.lstrip('/').replace('/', os.sep))
        data = open(p, 'rb').read() if os.path.exists(p) else rom[s:e]
        cls, note = classify(name, data)
        rows.append((fid, path, s, e, e - s, cls, note))

    if '--csv' in argv:
        print('fat_id,path,start,end,size,class,note')
        for fid, path, s, e, n, cls, note in rows:
            print('%d,%s,%d,%d,%d,%s,"%s"' % (fid, path, s, e, n, cls, note))
        return 0

    total = len(rom)
    named = sum(n for _, _, _, _, n, _, _ in rows)
    print('cartridge          %d bytes (device capacity byte 0x%02X)'
          % (total, r.devicecap))
    print('declared used      %d bytes' % r.hdr['ntr_rom_size'])
    print()

    # --- the cartridge, byte by byte -----------------------------------
    print('== where the cartridge went ==')
    parts = [
        ('header', 0, 0x4000),
        ('ARM9 module (secure area included)', r.hdr['arm9_rom_off'],
         r.hdr['arm9_rom_off'] + r.hdr['arm9_size']),
        ('ARM7 module', r.hdr['arm7_rom_off'],
         r.hdr['arm7_rom_off'] + r.hdr['arm7_size']),
        ('file name table', r.hdr['fnt_off'], r.hdr['fnt_off'] + r.hdr['fnt_size']),
        ('file allocation table', r.hdr['fat_off'],
         r.hdr['fat_off'] + r.hdr['fat_size']),
        ('banner', r.hdr['banner_off'], r.hdr['banner_off'] + 0xA00),
    ]
    accounted = 0
    for name, a, b in parts:
        print('  %-38s %10d  %6.3f%%' % (name, b - a, 100.0 * (b - a) / total))
        accounted += b - a
    print('  %-38s %10d  %6.3f%%' % ('files', named, 100.0 * named / total))
    accounted += named
    used = max(e for _, e in fat)
    slack = used - accounted
    print('  %-38s %10d  %6.3f%%  (inter-file alignment)'
          % ('slack inside the used area', slack, 100.0 * slack / total))
    tail = total - used
    zeros = sum(1 for b in rom[used:used + 1] ) and None
    z = rom[used:]
    nz = z.count(b'\x00'[0])
    nf = z.count(b'\xff'[0])
    print('  %-38s %10d  %6.3f%%  (%d zero, %d 0xFF)'
          % ('unused tail', tail, 100.0 * tail / total, nz, nf))
    print()

    # --- by class ------------------------------------------------------
    print('== files by class ==')
    agg = collections.Counter()
    cnt = collections.Counter()
    for _, _, _, _, n, cls, _ in rows:
        agg[cls] += n
        cnt[cls] += 1
    print('  %-24s %6s %12s %8s %8s'
          % ('CLASS', 'FILES', 'BYTES', '% CART', '% FILES'))
    for cls, b in agg.most_common():
        print('  %-24s %6d %12d %7.2f%% %7.2f%%'
              % (cls, cnt[cls], b, 100.0 * b / total, 100.0 * b / named))
    print('  %-24s %6d %12d %7.2f%% %7.2f%%'
          % ('TOTAL', len(rows), named, 100.0 * named / total, 100.0))
    print()

    # --- inside the containers -----------------------------------------
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ezbind
    print('== inside the EZBIND containers ==')
    magg = collections.Counter()
    mcnt = collections.Counter()
    arcs = 0
    for _, path, s0, e0, _, _, _ in rows:
        p = os.path.join(root, path.lstrip('/').replace(os.sep, os.sep)
                         .replace('/', os.sep))
        d = open(p, 'rb').read() if os.path.exists(p) else rom[s0:e0]
        d, how = ezbind.unwrap(d)
        if d[:8] != ezbind.MAGIC:
            continue
        try:
            ms = ezbind.parse(d)
        except ezbind.Bad:
            continue
        arcs += 1
        for n_off, size, off, tag in ms:
            nm = ezbind.name_at(d, n_off)
            cls, note = classify(nm, d[off:off + size])
            magg[cls] += size
            mcnt[cls] += 1
    mtot = sum(magg.values())
    print('  %d archives, %d members, %d bytes once decompressed'
          % (arcs, sum(mcnt.values()), mtot))
    print('  %-24s %6s %12s %8s' % ('CLASS', 'MEMBERS', 'BYTES', '% MEMBERS'))
    for cls, b in magg.most_common():
        print('  %-24s %6d %12d %7.2f%%'
              % (cls, mcnt[cls], b, 100.0 * b / mtot if mtot else 0))
    print()

    # --- how well the in-house formats are understood -------------------
    print('== the four in-house formats, checked by arithmetic ==')
    ok = collections.Counter()
    bad = collections.Counter()
    for _, path, _, _, _, _, note in rows:
        ext = path.rsplit('.', 1)[-1].lower()
        if ext in ('nbm', 'ana', 'apa', 'asc'):
            (bad if 'does not' in note else ok)[ext] += 1
    for ext in ('nbm', 'ana', 'apa', 'asc'):
        print('  .%-4s %5d of %5d satisfy the layout equation'
              % (ext, ok[ext], ok[ext] + bad[ext]))
    for _, path, _, _, n, _, note in rows:
        if 'does not' in note:
            print('    exception: %s (%d bytes) -- %s' % (path, n, note))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
