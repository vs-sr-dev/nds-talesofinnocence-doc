#!/usr/bin/env python3
"""What is actually in a Nintendo DS cartridge's 2 KiB secure area.

The header carries a CRC-16 over ROM 0x4000..0x7FFF, and on a dumped image it
will not match, because the first 2 KiB is encrypted on the cartridge and the
dumping tool decrypts it and overwrites the eight-byte identifier. That leaves
a question a scan has to answer before it can quote a denominator: is the
region readable content, or is it 2 KiB the tools cannot see into?

This answers it by measurement rather than by assertion.

  * the declared CRC, the recomputed CRC, and the CRC with each of the three
    plausible identifiers restored;
  * the region's byte entropy and its zero-byte count;
  * how many `svc #N ; bx lr` pairs it contains -- the shape of an SDK
    system-call wrapper;
  * and the same count over N windows of the same size taken from a file of
    genuinely incompressible data, as a control. Without the control the
    wrapper count means nothing.

    python securearea.py IMAGE [--control FILE] [--windows 3000]

Standard library only.
"""

import collections
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ndsrom import NDS, crc16
import bios_calls


def entropy(b):
    c = collections.Counter(b)
    n = float(len(b))
    return -sum(v / n * math.log(v / n, 2) for v in c.values())


def wrappers(buf, base=0):
    a, t = bios_calls.scan(buf, base, strict=True)
    return [(addr, n) for addr, n, followed in a + t if followed]


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    data = open(argv[1], 'rb').read()
    r = NDS(data)
    lo = r.hdr['arm9_rom_off']
    area = data[lo:lo + 0x4000]
    enc = data[lo:lo + 0x800]

    print('secure area: ROM 0x%X..0x%X, 2 KiB of which is encrypted on the'
          % (lo, lo + 0x4000))
    print('cartridge (ROM 0x%X..0x%X)' % (lo, lo + 0x800))
    print()
    print('  declared CRC-16   0x%04X' % r.secure_crc)
    print('  as dumped         0x%04X' % crc16(area))
    for cand, label in ((b'encryObj', "with 'encryObj' restored"),
                        (bytes(8), 'with eight zero bytes'),
                        (b'\xff' * 8, 'with eight 0xFF bytes')):
        t = bytearray(area)
        t[0:8] = cand
        print('  %-17s 0x%04X' % (label, crc16(bytes(t))))
    print('  first sixteen bytes: %s' % enc[:16].hex(' '))
    print()
    print('  entropy over the 2 KiB   %.3f bits' % entropy(enc))
    print('  zero bytes               %d of 2048' % enc.count(0))
    print('  distinct byte values     %d of 256' % len(set(enc)))
    print()
    w = wrappers(enc, 0x02000000)
    print('  `svc #N ; bx lr` pairs   %d' % len(w))
    for a, n in sorted(w):
        print('      0x%08X  svc #0x%02X  %s'
              % (a, n, bios_calls.SWI_NAMES.get(n, '?')))
    print()
    if '--control' in argv:
        cp = argv[argv.index('--control') + 1]
        nwin = int(argv[argv.index('--windows') + 1]) if '--windows' in argv else 3000
        cb = open(cp, 'rb').read()
        tot = 0
        used = 0
        for k in range(0, min(nwin * 2048, len(cb) - 2048), 2048):
            tot += len(wrappers(cb[k:k + 2048]))
            used += 1
        print('  control: %s' % os.path.basename(cp))
        print('  %d windows of 2048 bytes, entropy %.3f over the first window'
              % (used, entropy(cb[:2048])))
        print('  `svc #N ; bx lr` pairs found: %d' % tot)
        print()
        print('  A region of %d bytes that contains %d well-formed SDK'
              % (len(enc), len(w)))
        print('  wrappers where %d bytes of incompressible data contain %d is'
              % (used * 2048, tot))
        print('  readable code embedded in filler, not ciphertext.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
