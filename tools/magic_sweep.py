#!/usr/bin/env python3
"""Sweep the whole cartridge for every container tag the corpus knows.

Two families of needle:

  * **the corpus's own** -- the envelopes and project tags of the ten *Tales*
    builds documented so far, plus the middleware stamps that turned up beside
    them.  A hit would mean this build carries something one of those carried.
  * **the platform's** -- the Nitro container magics and the one-byte headers
    of the BIOS compression services, because on a Nintendo target the first
    question is what the machine already provides.

The denominator is printed with every line and it matters more here than
anywhere else in the corpus.  A four-byte needle turns up by chance about once
per 4 GB of uniform data.  On a 4.36 GB DVD that is one expected hit per
needle, so a single hit means nothing; on a 128 MB cartridge it is **0.031**
expected hits per needle, so a single hit is worth locating.  The reading of a
number changes with the size of the medium, and the number alone does not say
which is which.

    python magic_sweep.py IMAGE [--context]

Standard library only.
"""

import struct
import sys

CORPUS = [
    (b'CPS ', 'Legendia 2005 sixteen-byte envelope'),
    (b'CPS\x00', 'Legendia 2005 envelope, other spelling'),
    (b'TLPS', 'Tales container tag'),
    (b'TLPK', 'Tales container tag'),
    (b'AFS\x00', 'CRI AFS archive'),
    (b'SCPK', 'Destiny 2 2002 bundle'),
    (b'THEIRSCE', 'Tales script container'),
    (b'FILE.FPB', 'Destiny 2 2002 archive name'),
    (b'FPS2', 'Rebirth / Abyss archive'),
    (b'FPS3', 'Rebirth / Abyss archive'),
    (b'FPS4', 'Tales archive, later builds'),
    (b'MSCF', 'Microsoft cabinet'),
    (b'CVMH', 'CRI CVM volume header'),
    (b'ROFS', 'CRI ROFS volume'),
    (b'ROFSBLD', 'CRI ROFS builder stamp'),
    (b'SAMPLE_GAME_TITLE', 'CRI builder default title'),
    (b'TO7', 'Abyss project tag'),
    (b'TO8', 'project tag, next in the series'),
    (b'ToR', 'Rebirth project tag'),
    (b'ToL', 'Legendia project tag'),
    (b'tox', 'Legendia project directory'),
    (b'tor_', 'Rebirth sound-effect prefix'),
    (b'VAGp', 'Sony ADPCM'),
    (b'KORG', 'sound bank'),
    (b'ADX', 'CRI ADX'),
    (b'.slz', 'Abyss compressed-member extension'),
    (b'SLZ', 'Abyss compressed-member extension, upper case'),
]

PLATFORM = [
    (b'SDAT', 'Nitro sound archive'),
    (b'NARC', 'Nitro archive'),
    (b'BMD0', 'Nitro 3D model'),
    (b'BTX0', 'Nitro 3D texture'),
    (b'BCA0', 'Nitro 3D joint animation'),
    (b'BTA0', 'Nitro 3D texture animation'),
    (b'BMA0', 'Nitro 3D material animation'),
    (b'BVA0', 'Nitro 3D visibility animation'),
    (b'BTP0', 'Nitro 3D texture-pattern animation'),
    (b'RLCN', 'Nitro palette (NCLR)'),
    (b'RGCN', 'Nitro character graphics (NCGR)'),
    (b'RCSN', 'Nitro screen (NSCR)'),
    (b'RECN', 'Nitro cell (NCER)'),
    (b'RNAN', 'Nitro cell animation (NANR)'),
    (b'SSEQ', 'Nitro sequence'),
    (b'SWAR', 'Nitro wave archive'),
    (b'SBNK', 'Nitro bank'),
    (b'STRM', 'Nitro stream'),
    (b'SWAV', 'Nitro wave'),
    (b'VXDS', 'Actimagine VX video'),
    (b'IMD ', 'Nitro intermediate model, XML'),
]


def count(data, needle):
    n, i = 0, data.find(needle)
    firsts = []
    while i != -1:
        n += 1
        if len(firsts) < 8:
            firsts.append(i)
        i = data.find(needle, i + 1)
    return n, firsts


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    data = open(argv[1], 'rb').read()
    ctx = '--context' in argv
    n = len(data)
    print('%s -- %d bytes' % (argv[1], n))
    print('expected chance hits for a four-byte needle in this image: %.4f'
          % (n / 2.0 ** 32))
    print('(the same needle in a 4.36 GB DVD would expect %.2f)'
          % (4357816320 / 2.0 ** 32))
    print()
    for title, table in (('corpus markers', CORPUS), ('platform magics', PLATFORM)):
        print('== %s ==' % title)
        print('%-20s %8s  %s' % ('NEEDLE', 'HITS', 'FIRST OFFSETS'))
        for needle, what in table:
            c, firsts = count(data, needle)
            print('%-20s %8d  %s   %s'
                  % (needle.decode('latin1').replace('\x00', '\\0'), c,
                     ' '.join('0x%X' % f for f in firsts) if c else '-', what))
            if ctx and c and c <= 40:
                for f in firsts:
                    print('        0x%08X  %r' % (f, data[max(0, f - 8):f + 40]))
        print()
    print('== BIOS compression headers, as the first byte of an aligned word ==')
    print('A type byte alone means nothing; these are the offsets where a')
    print('BIOS-format header is followed by a plausible decompressed size.')
    for t, name in ((0x10, 'LZ77'), (0x11, 'LZ11'), (0x24, 'Huffman4'),
                    (0x28, 'Huffman8'), (0x30, 'RLE'), (0x81, 'Diff8'),
                    (0x82, 'Diff16')):
        raw = plaus = 0
        for i in range(0, n - 4, 4):
            if data[i] != t:
                continue
            raw += 1
            size = data[i + 1] | (data[i + 2] << 8) | (data[i + 3] << 16)
            if 64 <= size <= 8 << 20:
                plaus += 1
        print('  0x%02X %-9s %9d aligned words start with it, %8d have a '
              'plausible size' % (t, name, raw, plaus))


if __name__ == '__main__':
    main(sys.argv)
