#!/usr/bin/env python3
"""Every date this cartridge states about itself.

A DS cartridge has no volume descriptor and its file allocation table carries
no timestamps, so the only dates are the ones a compiler, an exporter or a
middleware build stamped into a payload.  Four shapes are looked for, over the
whole image, and each hit is located in the file system so it can be attributed:

  1. `__DATE__` / `__TIME__` as the C preprocessor writes them --
     `Mmm dd yyyy` and `hh:mm:ss`, and the pair when they are adjacent;
  2. ISO-ish dates, `yyyy/mm/dd` and `yyyy-mm-dd`;
  3. middleware build strings, which name themselves -- `Build:`, `Ver.`,
     `version`;
  4. eight-digit and six-digit date groups inside file and texture names,
     `yyyymmdd` and `yymmdd`, filtered to plausible ranges.

Nothing here is inferred from the ROM's file name or from a catalogue.

    python datestamps.py IMAGE [--fat] [--context N]

Standard library only.
"""

import os
import re
import struct
import sys

MONTHS = ('Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec')

PATTERNS = [
    ('C __DATE__ __TIME__',
     re.compile((r'(?:' + MONTHS + r')[ ] [ 0-3]?\d [12]\d{3}'
                 r'(?:[^\x00-\x1f]{0,8}[0-2]\d:[0-5]\d:[0-5]\d)?').encode())),
    ('ISO date', re.compile(rb'[12]\d{3}[/-](?:0[1-9]|1[0-2])[/-]'
                            rb'(?:0[1-9]|[12]\d|3[01])')),
    ('build string', re.compile(rb'[\x20-\x7e]{0,40}'
                                rb'(?:Build:|Ver\.|version )[\x20-\x7e]{0,40}')),
]

NAME_DATE = re.compile(rb'(?<![0-9])((?:19|20)\d{2}(?:0[1-9]|1[0-2])'
                       rb'(?:0[1-9]|[12]\d|3[01]))(?![0-9])')
NAME_DATE6 = re.compile(rb'(?<![0-9])(0[4-9](?:0[1-9]|1[0-2])'
                        rb'(?:0[1-9]|[12]\d|3[01]))(?![0-9])')


class Locator(object):
    """Which FAT file, if any, an image offset lands in."""

    def __init__(self, rom):
        self.rom = rom
        fat_off, fat_size = struct.unpack_from('<II', rom, 0x48)
        self.ent = [struct.unpack_from('<II', rom, fat_off + 8 * i)
                    for i in range(fat_size // 8)]
        self.starts = sorted((s, e, i) for i, (s, e) in enumerate(self.ent))
        self.names = {}
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from ndsrom import NDS
            files, dirs = NDS(rom).fnt()
            self.names = dict(files)
        except Exception:
            pass
        self.a9 = struct.unpack_from('<II', rom, 0x20)[0], \
            struct.unpack_from('<I', rom, 0x2C)[0]
        self.a7 = struct.unpack_from('<I', rom, 0x30)[0], \
            struct.unpack_from('<I', rom, 0x3C)[0]

    def where(self, off):
        a, n = self.a9
        if a <= off < a + n:
            return 'arm9.bin+0x%X' % (off - a)
        a, n = self.a7
        if a <= off < a + n:
            return 'arm7.bin+0x%X' % (off - a)
        for s, e, i in self.starts:
            if s <= off < e:
                return '%s+0x%X' % (self.names.get(i, 'FAT file %d' % i),
                                    off - s)
        return 'outside the file system'


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    rom = open(argv[1], 'rb').read()
    loc = Locator(rom)
    ctx = int(argv[argv.index('--context') + 1], 0) if '--context' in argv else 0

    for label, pat in PATTERNS:
        hits = list(pat.finditer(rom))
        seen = {}
        for m in hits:
            seen.setdefault(m.group().strip(), []).append(m.start())
        print('== %s: %d hits, %d distinct =='
              % (label, len(hits), len(seen)))
        for text, offs in sorted(seen.items(), key=lambda kv: -len(kv[1]))[:40]:
            try:
                t = text.decode('shift_jis', 'replace')
            except Exception:
                t = repr(text)
            print('  %-58s x%-4d  0x%08X  %s'
                  % (t[:58], len(offs), offs[0], loc.where(offs[0])))
            if ctx:
                for o in offs[:ctx]:
                    print('        0x%08X  %s' % (o, loc.where(o)))
        print()

    print('== eight-digit date groups in names ==')
    seen = {}
    for m in NAME_DATE.finditer(rom):
        seen.setdefault(m.group(1), []).append(m.start())
    for text, offs in sorted(seen.items()):
        print('  %s  x%-4d  0x%08X  %s'
              % (text.decode(), len(offs), offs[0], loc.where(offs[0])))
    if not seen:
        print('  none')
    print()

    print('== six-digit yymmdd groups in names, 2004-2009 ==')
    seen = {}
    for m in NAME_DATE6.finditer(rom):
        seen.setdefault(m.group(1), []).append(m.start())
    for text, offs in sorted(seen.items())[:60]:
        print('  %s  x%-4d  0x%08X  %s'
              % (text.decode(), len(offs), offs[0], loc.where(offs[0])))
    print('  %d distinct groups' % len(seen))


if __name__ == '__main__':
    main(sys.argv)
