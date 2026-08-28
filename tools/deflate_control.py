#!/usr/bin/env python3
"""How compressible is this cartridge, and which parts of it are already packed?

The constant scan and the structural probe both depend on having guessed the
right fingerprint.  This one does not depend on anything: run every byte
through `zlib` at level 9 and see what comes back.  Data that a packer has
already been over does not shrink again; data stored raw does.

On *Tales of the Tempest* the whole cartridge deflated to 52.6%, its palettes
to 9.3% and its bitmaps to 16.1%, and that -- three measurements agreeing with
a branch count and a header census -- is what made "the data is stored raw"
safe to say.  The same numbers on a cartridge that *does* compress should look
different, and the interesting reading is per class rather than in total,
because one large already-compressed medium moves the total on its own.

`--class` re-uses `formats.py`'s classifier so the rows mean the same thing
they do in the budget.

    python deflate_control.py IMAGE FILESDIR
    python deflate_control.py IMAGE FILESDIR --class

Standard library only.
"""

import collections
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import formats


def ratio(b):
    if not b:
        return 0.0
    return 100.0 * len(zlib.compress(b, 9)) / len(b)


def walk_files(root):
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
    rom_path, root = argv[1], argv[2]
    rom = open(rom_path, 'rb').read()

    print('== the image as a whole ==')
    print('  %-34s %11d bytes  deflates to %6.2f%%'
          % (os.path.basename(rom_path), len(rom), ratio(rom)))
    print()

    print('== the parts of it ==')
    d = os.path.dirname(rom_path)
    for n in ('arm9.bin', 'arm7.bin', 'overlay_0.bin', 'overlay_1.bin',
              'overlay_2.bin'):
        p = os.path.join(d, n)
        if os.path.exists(p):
            b = open(p, 'rb').read()
            print('  %-34s %11d bytes  deflates to %6.2f%%'
                  % (n, len(b), ratio(b)))
    print()

    agg = collections.defaultdict(lambda: [0, 0, 0])
    for rel, p in walk_files(root):
        b = open(p, 'rb').read()
        cls, note = formats.classify(os.path.basename(rel), b)
        if ', in a BIOS ' in note:
            cls = cls + ' (already in a BIOS stream)'
        row = agg[cls]
        row[0] += 1
        row[1] += len(b)
        row[2] += len(zlib.compress(b, 9))
    print('== the files, by the budget\'s own classes ==')
    print('  %-24s %6s %13s %13s %8s'
          % ('CLASS', 'FILES', 'BYTES', 'DEFLATED', 'RATIO'))
    tn = tb = tc = 0
    for cls, (n, b, c) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
        tn += n
        tb += b
        tc += c
        print('  %-24s %6d %13d %13d %7.2f%%'
              % (cls, n, b, c, 100.0 * c / b if b else 0))
    print('  %-24s %6d %13d %13d %7.2f%%'
          % ('TOTAL', tn, tb, tc, 100.0 * tc / tb if tb else 0))


if __name__ == '__main__':
    main(sys.argv)
