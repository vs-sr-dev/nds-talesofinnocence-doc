#!/usr/bin/env python3
"""The decompressors a Nintendo DS gives you for free, plus the linker's own.

Section 7's rule for a non-console target is to ask what the platform already
supplies before proving a custom codec absent.  On the DS that is five BIOS
services with a one-byte header, and one more format that is not a BIOS
service at all: `BLZ`, the backwards LZ the Nintendo linker applies to
`arm9.bin` and to overlays.  A scan of a *compressed* `arm9.bin` returns zero
and looks exactly like a clean negative, which is why the decompressor comes
before the constant scan and not after it.

Formats:

  0x10  LZ77   (`LZ77UnComp`)      8 control bits, MSB first, 1 = match
  0x11  LZ11                       three token widths, DS-only
  0x24  Huffman, 4-bit symbols
  0x28  Huffman, 8-bit symbols
  0x30  RLE    (`RLUnComp`)
  0x81  8-bit difference filter    (a filter, not a compressor)
  0x82  16-bit difference filter

The difference-filter type byte is `0x80 | width_code`, and the width code is
1 for 8-bit and 2 for 16-bit -- so the two filters are `0x81` and `0x82`, not
`0x80` and `0x81`.  This file had them one place low until a cartridge turned
up carrying a filtered stream to check against: *Tales of Innocence* ships one
animation five times over, once per format, and `01_DIFF.bin` is type `0x82`
and unfilters to `01.nsbca` byte for byte.  `0x80` is not a stream type.

  header: u8 type, u24 LE decompressed size; if that size is 0, a u32 follows.

  BLZ: no header.  An 8-byte footer -- u24 compressed length, u8 header size,
  u32 length delta -- and the stream is read and written backwards.

Usage:
  python ndscomp.py --info FILE            what, if anything, this file is
  python ndscomp.py --decomp FILE OUT      decompress it
  python ndscomp.py --blz FILE OUT         un-BLZ it (arm9.bin, overlays)
  python ndscomp.py --scan FILE            every embedded stream that decodes
  python ndscomp.py --verify FILE REF      decompress FILE and compare with REF
  python ndscomp.py --census DIR           one line per file over a tree

`--census` and `--sweep` walk the tree recursively.  On *Tales of the Tempest*
every file lived in one flat directory and `os.listdir` was enough; this
cartridge has 156 of them, and a flat listing silently measures nothing.

Standard library only.
"""

import os
import struct
import sys

TYPES = {0x10: 'LZ77', 0x11: 'LZ11', 0x24: 'Huffman4', 0x28: 'Huffman8',
         0x30: 'RLE', 0x81: 'Diff8', 0x82: 'Diff16'}

# Which of the seven a sweep can actually rule out, which is fewer than it
# looks and is worth stating rather than glossing.
#
#   LZ77 (0x10) -- discriminating.  It rejects a back-reference before the
#     start of the output, and its geometry caps the compression ratio: a
#     two-byte token yields at most eighteen bytes and costs an eighth of a
#     flag byte besides, so no LZ77 stream can exceed 18 / 2.125 = 8.47x.
#     Both tests come from the format, not from taste.
#   LZ11 (0x11) -- rejects the same back-references, but its four-byte token
#     reaches 65,808 bytes, so the ratio bound is useless and random data
#     produces plausible-looking streams.
#   Huffman (0x24, 0x28) -- a small tree walks arbitrary bits happily; nothing
#     in the format says the output is wrong.
#   RLE (0x30) and the difference filters (0x81, 0x82) -- *every* byte
#     sequence is a valid stream.
#
# So the sweep runs on LZ77 and the rest are reported by header count, with
# that stated, rather than by a hit count that would measure the type byte.
DISCRIMINATING = {0x10}
MAX_LZ77_RATIO = 18.0 / 2.125
PERMISSIVE = {0x11, 0x24, 0x28, 0x30, 0x81, 0x82}


class Bad(Exception):
    pass


def header(buf, off=0):
    if off + 4 > len(buf):
        raise Bad('short')
    t = buf[off]
    if t not in TYPES:
        raise Bad('type 0x%02X' % t)
    size = buf[off + 1] | (buf[off + 2] << 8) | (buf[off + 3] << 16)
    n = 4
    if size == 0:
        if off + 8 > len(buf):
            raise Bad('short')
        size = struct.unpack_from('<I', buf, off + 4)[0]
        n = 8
    return t, size, n


def lz77(buf, off, size, out_len):
    out = bytearray()
    p = off
    while len(out) < out_len:
        if p >= len(buf):
            raise Bad('input exhausted')
        flags = buf[p]
        p += 1
        for b in range(8):
            if len(out) >= out_len:
                break
            if flags & (0x80 >> b):
                if p + 1 >= len(buf):
                    raise Bad('input exhausted')
                a, c = buf[p], buf[p + 1]
                p += 2
                n = (a >> 4) + 3
                d = (((a & 0xF) << 8) | c) + 1
                if d > len(out):
                    raise Bad('back-reference before the start')
                for _ in range(n):
                    out.append(out[len(out) - d])
            else:
                if p >= len(buf):
                    raise Bad('input exhausted')
                out.append(buf[p])
                p += 1
    return bytes(out[:out_len]), p - off


def lz11(buf, off, size, out_len):
    out = bytearray()
    p = off
    while len(out) < out_len:
        if p >= len(buf):
            raise Bad('input exhausted')
        flags = buf[p]
        p += 1
        for b in range(8):
            if len(out) >= out_len:
                break
            if not flags & (0x80 >> b):
                if p >= len(buf):
                    raise Bad('input exhausted')
                out.append(buf[p])
                p += 1
                continue
            if p >= len(buf):
                raise Bad('input exhausted')
            ind = buf[p] >> 4
            if ind == 0:                      # 3 bytes, length 17..272
                if p + 2 >= len(buf):
                    raise Bad('input exhausted')
                n = (((buf[p] & 0xF) << 4) | (buf[p + 1] >> 4)) + 17
                d = (((buf[p + 1] & 0xF) << 8) | buf[p + 2]) + 1
                p += 3
            elif ind == 1:                    # 4 bytes, length 273..65808
                if p + 3 >= len(buf):
                    raise Bad('input exhausted')
                n = (((buf[p] & 0xF) << 12) | (buf[p + 1] << 4)
                     | (buf[p + 2] >> 4)) + 273
                d = (((buf[p + 2] & 0xF) << 8) | buf[p + 3]) + 1
                p += 4
            else:                             # 2 bytes, length 3..16
                if p + 1 >= len(buf):
                    raise Bad('input exhausted')
                n = ind + 1
                d = (((buf[p] & 0xF) << 8) | buf[p + 1]) + 1
                p += 2
            if d > len(out):
                raise Bad('back-reference before the start')
            for _ in range(n):
                out.append(out[len(out) - d])
    return bytes(out[:out_len]), p - off


def rle(buf, off, size, out_len):
    out = bytearray()
    p = off
    while len(out) < out_len:
        if p >= len(buf):
            raise Bad('input exhausted')
        f = buf[p]
        p += 1
        if f & 0x80:
            n = (f & 0x7F) + 3
            if p >= len(buf):
                raise Bad('input exhausted')
            out.extend(bytes([buf[p]]) * n)
            p += 1
        else:
            n = (f & 0x7F) + 1
            if p + n > len(buf):
                raise Bad('input exhausted')
            out.extend(buf[p:p + n])
            p += n
    return bytes(out[:out_len]), p - off


def huffman(buf, off, size, out_len, bits):
    """The BIOS Huffman, 4- or 8-bit symbols.

    A tree size byte, then a byte array of nodes whose first element is the
    root.  For a node at address `a` holding value `n`, the children are at

        (a & ~1) + (n & 0x3F) * 2 + 2  + bit

    and the child reached by `bit` is a leaf when `n & (0x80 >> bit)` -- bit 7
    flags the zero-child, bit 6 the one-child.  The bitstream that follows is
    read as little-endian 32-bit words, most significant bit first.  For 4-bit
    symbols the first of each pair is the **low** nibble of the output byte.

    Two things here were wrong until a cartridge supplied a stream to check
    against.  The leaf mask was `0x40 >> bit`, which tests the wrong two bits;
    and the child address was computed from an index relative to the tree
    rather than from the node's own address, which loses the `& ~1` alignment
    whenever the tree starts at an odd address -- and it always does, because
    the tree size byte sits in front of it.  Both failures come out as
    `tree overrun` or `input exhausted`, which read exactly like a file that
    is not Huffman at all.  *Tales of Innocence* ships one animation five
    times over, once per format: `00_HUFF.bin` (8-bit) and `01_HUFF.bin`
    (4-bit) now decode to `00.nsbca` and `01.nsbca` byte for byte.
    """
    if off >= len(buf):
        raise Bad('short')
    tree_size = (buf[off] + 1) * 2
    tree_start = off + 1
    tree_end = off + tree_size
    if tree_end > len(buf):
        raise Bad('short tree')
    p = tree_end
    out = bytearray()
    nyb = []
    pos = tree_start
    node = buf[tree_start]
    while len(out) < out_len:
        if p + 3 >= len(buf):
            raise Bad('input exhausted')
        word = struct.unpack_from('<I', buf, p)[0]
        p += 4
        for b in range(31, -1, -1):
            if len(out) >= out_len:
                break
            bit = (word >> b) & 1
            child = (pos & ~1) + (node & 0x3F) * 2 + 2 + bit
            if child >= tree_end:
                raise Bad('tree overrun')
            leaf = node & (0x80 >> bit)
            v = buf[child]
            if leaf:
                if bits == 8:
                    out.append(v)
                else:
                    nyb.append(v & 0xF)
                    if len(nyb) == 2:
                        out.append(nyb[0] | (nyb[1] << 4))
                        nyb = []
                pos = tree_start
                node = buf[tree_start]
            else:
                pos = child
                node = v
    return bytes(out[:out_len]), p - off


def diff(buf, off, size, out_len, wide):
    out = bytearray()
    p = off
    if not wide:
        cur = 0
        while len(out) < out_len:
            if p >= len(buf):
                raise Bad('input exhausted')
            cur = (cur + buf[p]) & 0xFF
            p += 1
            out.append(cur)
    else:
        cur = 0
        while len(out) < out_len:
            if p + 1 >= len(buf):
                raise Bad('input exhausted')
            cur = (cur + struct.unpack_from('<H', buf, p)[0]) & 0xFFFF
            p += 2
            out.extend(struct.pack('<H', cur))
    return bytes(out[:out_len]), p - off


def decompress(buf, off=0, limit=None):
    """Decompress one BIOS-format stream at `off`.  Returns (data, consumed).

    `limit` stops after that many output bytes.  It is there for the sweep:
    a stream that is not one usually fails inside the first few dozen tokens
    -- a back-reference before the start of the output, or the input running
    out -- so decoding 256 bytes prunes almost everything at a two-hundredth
    of the cost, and only the survivors are decoded in full.
    """
    t, out_len, n = header(buf, off)
    want = out_len if limit is None else min(out_len, limit)
    body = off + n
    if t == 0x10:
        d, used = lz77(buf, body, out_len, want)
    elif t == 0x11:
        d, used = lz11(buf, body, out_len, want)
    elif t == 0x30:
        d, used = rle(buf, body, out_len, want)
    elif t == 0x24:
        d, used = huffman(buf, body, out_len, want, 4)
    elif t == 0x28:
        d, used = huffman(buf, body, out_len, want, 8)
    elif t == 0x81:
        d, used = diff(buf, body, out_len, want, False)
    elif t == 0x82:
        d, used = diff(buf, body, out_len, want, True)
    else:
        raise Bad('unhandled 0x%02X' % t)
    return d, n + used


# ------------------------------------------------------------------ BLZ

def blz_decompress(data):
    """The backwards LZ the Nintendo linker applies to arm9.bin and overlays.

    A scan of a still-compressed module finds nothing and looks like a clean
    negative, so this runs first.  A module that is not BLZ-compressed says so
    in its own footer -- the length delta is zero -- and that is a fact worth
    reporting rather than an error.
    """
    if len(data) < 8:
        raise Bad('too short')
    inc_len = struct.unpack_from('<I', data, len(data) - 4)[0]
    if inc_len == 0:
        raise Bad('length delta is zero: this module is not BLZ-compressed')
    hdr_len = data[len(data) - 5]
    if not 8 <= hdr_len <= 11:
        raise Bad('header length %d out of range: not BLZ' % hdr_len)
    enc_len = struct.unpack_from('<I', data, len(data) - 8)[0] & 0xFFFFFF
    dec_len = len(data) + inc_len
    if enc_len > len(data):
        raise Bad('encoded length beyond the file')
    raw = len(data) - enc_len
    out = bytearray(data[:len(data)])
    out.extend(b'\x00' * inc_len)
    src = raw + enc_len - hdr_len
    dst = dec_len
    end = raw
    mask, flags = 0, 0
    while dst > end:
        mask >>= 1
        if mask == 0:
            src -= 1
            if src < end:
                raise Bad('input exhausted')
            flags = out[src]
            mask = 0x80
        if not flags & mask:
            src -= 1
            dst -= 1
            out[dst] = out[src]
        else:
            src -= 2
            if src < end:
                raise Bad('input exhausted')
            pos = ((out[src] << 8) | out[src + 1])
            n = (pos >> 12) + 3
            pos = (pos & 0xFFF) + 3
            for _ in range(n):
                dst -= 1
                out[dst] = out[dst + pos]
    return bytes(out[:dec_len])


# ------------------------------------------------------------------ scanning

def scan(buf, min_out=64, step=4, max_out=8 << 20):
    """Every offset at which a BIOS-format stream decodes cleanly.

    Returns (hits, tried).  `tried` is the denominator: how many offsets got
    as far as an attempted decompression.  Nintendo containers align their
    members, so `step` defaults to 4; pass 1 for an exhaustive sweep.
    """
    hits = []
    tried = 0
    probed = 0
    n = len(buf)
    for off in range(0, n - 8, step):
        t = buf[off]
        if t not in DISCRIMINATING:
            continue
        size = buf[off + 1] | (buf[off + 2] << 8) | (buf[off + 3] << 16)
        if not min_out <= size <= max_out:
            continue
        tried += 1
        try:
            decompress(buf, off, limit=256)
        except (Bad, IndexError, MemoryError):
            continue
        probed += 1
        try:
            d, used = decompress(buf, off)
        except (Bad, IndexError, MemoryError):
            continue
        # A stream that consumed more input than it produced did not compress
        # anything, and one that claims more than the format's own maximum
        # ratio is not a stream at all.
        if (len(d) >= min_out and used < len(d)
                and len(d) <= used * MAX_LZ77_RATIO):
            hits.append((off, t, len(d), used))
    return hits, (tried, probed)


def info(path):
    data = open(path, 'rb').read()
    try:
        t, out_len, n = header(data, 0)
    except Bad as e:
        return '%-40s %9d  not a BIOS-compressed stream (%s)' % (
            os.path.basename(path), len(data), e)
    try:
        d, used = decompress(data, 0)
    except Bad as e:
        return '%-40s %9d  header says %s %d but does not decode (%s)' % (
            os.path.basename(path), len(data), TYPES[t], out_len, e)
    return '%-40s %9d  %-9s -> %d bytes, %d consumed of %d' % (
        os.path.basename(path), len(data), TYPES[t], len(d), used, len(data))


def walk_files(root):
    """Every file under root, relative path and full path, sorted.

    The flat `os.listdir` this originally used measures zero files on a
    cartridge whose file system has directories in it, and says so in the
    same words it would use for a real negative."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            out.append((os.path.relpath(full, root).replace(os.sep, '/'), full))
    out.sort()
    return out


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    mode = argv[1]
    if mode == '--info':
        for p in argv[2:]:
            print(info(p))
    elif mode == '--decomp':
        d, used = decompress(open(argv[2], 'rb').read())
        open(argv[3], 'wb').write(d)
        print('%d bytes' % len(d))
    elif mode == '--blz':
        try:
            d = blz_decompress(open(argv[2], 'rb').read())
        except Bad as e:
            print('%s: %s' % (argv[2], e))
            return
        open(argv[3], 'wb').write(d)
        print('%d bytes' % len(d))
    elif mode == '--scan':
        buf = open(argv[2], 'rb').read()
        step = int(argv[argv.index('--step') + 1], 0) if '--step' in argv else 4
        hits, (tried, probed) = scan(buf, step=step)
        print('%s' % argv[2])
        print('  %d bytes, swept at step %d' % (len(buf), step))
        print('  %d offsets carry a BIOS type byte and a plausible size'
              % tried)
        print('  %d of those survive a 256-byte trial decode' % probed)
        print('  %d of those decode in full and actually compressed something'
              % len(hits))
        for off, t, n, used in hits[:200]:
            print('    0x%08X %-9s %d bytes from %d' % (off, TYPES[t], n, used))
    elif mode == '--sweep':
        # One file at a time.  Sweeping a whole cartridge image in one buffer
        # is the wrong shape of test: a candidate is bounded by whether its
        # declared stream fits in the buffer, which inside a 64 KB file
        # rejects nearly everything for nothing and inside a 134 MB image
        # rejects almost nothing.  Per file, every byte is still covered and
        # the bound does its job.
        root = argv[2]
        step = int(argv[argv.index('--step') + 1], 0) if '--step' in argv else 4
        tot_tried = tot_probed = tot_hits = tot_bytes = files = 0
        for fn, p in walk_files(root):
            buf = open(p, 'rb').read()
            files += 1
            tot_bytes += len(buf)
            hits, (tried, probed) = scan(buf, step=step)
            tot_tried += tried
            tot_probed += probed
            tot_hits += len(hits)
            for off, t, n, used in hits:
                print('  %-44s 0x%08X %-9s %d bytes from %d'
                      % (fn, off, TYPES[t], n, used))
        print('# %d files, %d bytes, swept at step %d' % (files, tot_bytes, step))
        print('# formats swept: %s'
              % ', '.join(TYPES[t] for t in sorted(DISCRIMINATING)))
        print('# formats NOT swept, because every byte sequence is a valid')
        print('# stream in them and a hit would measure the type byte only: %s'
              % ', '.join(TYPES[t] for t in sorted(PERMISSIVE)))
        print('# %d offsets carried a type byte and a plausible size' % tot_tried)
        print('# %d of those survived a 256-byte trial decode' % tot_probed)
        print('# %d decoded in full and actually compressed something' % tot_hits)
    elif mode == '--verify':
        # The one test that does not depend on a heuristic: decompress a
        # stream and compare it with the file it was made from.  *Tales of
        # Innocence* left one animation on the cartridge five times over,
        # once per format, next to the original -- which is the only positive
        # control this corpus has ever had for these decoders, and it found
        # two defects in them.
        data = open(argv[2], 'rb').read()
        ref = open(argv[3], 'rb').read()
        try:
            d, used = decompress(data, 0)
        except (Bad, IndexError) as e:
            print('%-24s %7d  type 0x%02X  FAILED: %s'
                  % (os.path.basename(argv[2]), len(data),
                     data[0] if data else 0, e))
            return
        print('%-24s %7d  0x%02X %-9s -> %7d  consumed %d/%d  identical to %s: %s'
              % (os.path.basename(argv[2]), len(data), data[0],
                 TYPES.get(data[0], '?'), len(d), used, len(data),
                 os.path.basename(argv[3]), 'YES' if d == ref else 'NO'))
    elif mode == '--census':
        root = argv[2]
        tot = ok = 0
        packed = unpacked = 0
        by_type = {}
        header_only = {}
        for fn, p in walk_files(root):
            tot += 1
            data = open(p, 'rb').read()
            if len(data) >= 4 and data[0] in TYPES:
                sz = data[1] | data[2] << 8 | data[3] << 16
                if sz:
                    header_only[data[0]] = header_only.get(data[0], 0) + 1
            try:
                d, used = decompress(data, 0)
                if len(d) < 32 or used != len(data):
                    continue
                ok += 1
                packed += len(data)
                unpacked += len(d)
                t = TYPES[data[0]]
                a, b, c = by_type.get(t, (0, 0, 0))
                by_type[t] = (a + 1, b + len(data), c + len(d))
                print('%-44s %9d  %-9s -> %9d' % (fn, len(data), t, len(d)))
            except (Bad, IndexError):
                pass
        print('# %d of %d files begin with a BIOS-format stream that decodes'
              % (ok, tot))
        print('# and consumes the whole file')
        for t in sorted(by_type):
            n, a, b = by_type[t]
            print('#   %-9s %5d files  %11d -> %11d  %.2fx'
                  % (t, n, a, b, b / a if a else 0))
        if ok:
            print('#   %-9s %5d files  %11d -> %11d  %.2fx'
                  % ('TOTAL', ok, packed, unpacked,
                     unpacked / packed if packed else 0))
        print('#')
        print('# for comparison, files whose first byte is a BIOS type byte and')
        print('# whose next three are a non-zero size -- the header shape alone,')
        print('# which for the permissive formats is all a census can measure:')
        for t in sorted(header_only):
            print('#   0x%02X %-9s %5d files%s'
                  % (t, TYPES[t], header_only[t],
                     '' if t in DISCRIMINATING else
                     '   (permissive: any byte sequence decodes)'))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main(sys.argv)
