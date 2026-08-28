#!/usr/bin/env python3
"""Read every site the two scans flagged, rather than dismissing them.

Section 7, step 4: *investigate every near-miss.*  On *Tales of Legendia* six
of seven sites were innocent and reading them was the point; on *Tales of the
Abyss*, four of six.  A negative is only worth quoting if the positives inside
it were read.

This re-runs the hit-finding halves of `ring_sites.py` and `struct_probe.py`
and disassembles around each hit, in both instruction sets, so the reader can
see what the site actually is.  For a hit at an even-but-not-word offset it
also prints the ARM word that contains it, because a THUMB decode of ARM code
is the standard way to invent a fingerprint that is not there.

    python nearmiss.py FILE [--base VA] [--imm 4078,4079,4080,4070,4071]

Standard library only.
"""

import math
import struct
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
import disarm
import ring_sites
import struct_probe

TRIG_HEAD = """
   * what the 4080 sites actually are
     The `mov r0,#4080` instructions all sit in one region of eight-byte
     stubs -- `mov r0,#K ; bx lr` or `ldr r0,[pc,..] ; bx lr` -- reached by a
     table of `b` instructions above them, which is the ARM computed-branch
     idiom.  What they return is a 4,096-scaled trigonometric table in whole
     degrees."""


def show(data, base, off, n=6, thumb=False, pre=4):
    start = off - pre * (2 if thumb else 4)
    if start < 0:
        start = 0
    for line in disarm.disasm(data, start, n, base, thumb):
        print('      ' + line)


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    path = argv[1]
    data = open(path, 'rb').read()
    base = int(argv[argv.index('--base') + 1], 0) if '--base' in argv else 0
    wanted = (4078, 4079, 4080, 4070, 4071)
    if '--imm' in argv:
        wanted = tuple(int(x, 0) for x in argv[argv.index('--imm') + 1].split(','))

    print('=' * 72)
    print('%s -- every site the constant scan and the structure probe found'
          % path)
    print('=' * 72)

    imm_hits, imm_total = ring_sites.arm_immediates(data, base, wanted)
    th_hits, th_total = ring_sites.thumb_immediates(data, base, wanted)
    targets, _, _ = ring_sites.pc_relative_targets(data, base)
    lit_hits, lit_total = ring_sites.literal_words(data, base, wanted, targets)

    print('\n-- ARM immediate fields matching %s (%d instructions scanned) --'
          % (', '.join(str(x) for x in wanted), imm_total))
    for va, w, name, val in imm_hits:
        print('    0x%08X  %s' % (va, name))
        show(data, base, va - base)
        print()
    if not imm_hits:
        print('    none')

    print('\n-- THUMB literal fields matching the same set (%d scanned) --'
          % th_total)
    for va, h, name, val in th_hits:
        print('    0x%08X  %s' % (va, name))
        show(data, base, va - base, 8, thumb=True)
        print('      containing ARM word: 0x%08X  %s'
              % (struct.unpack_from('<I', data, (va - base) & ~3)[0],
                 disarm.arm(struct.unpack_from('<I', data, (va - base) & ~3)[0],
                            base + ((va - base) & ~3))))
        print()
    if not th_hits:
        print('    none')

    print('\n-- 32-bit words in the pool equal to one of the constants '
          '(%d words scanned) --' % lit_total)
    for va, w, refs in lit_hits:
        o = va - base
        print('    0x%08X  = %d  %s' % (va, w,
                                        'referenced by %d PC-relative load(s)'
                                        % len(refs) if refs
                                        else 'NOT referenced by any '
                                             'PC-relative load'))
        print('      neighbouring words: %s'
              % ' '.join('%08X' % struct.unpack_from('<I', data, j)[0]
                         for j in range(max(0, o - 8), min(len(data) - 3, o + 12), 4)))
        print()
    if not lit_hits:
        print('    none')

    print('\n-- the structure probe\'s sites --')
    dp = list(struct_probe.arm_dp(data))
    sh = list(struct_probe.arm_shifts(data))
    tsh = list(struct_probe.thumb_shifts(data))
    timm = list(struct_probe.thumb_imm(data))

    print('\n   * every immediate equal to 0xFF00 (the control-register refill '
          'would be an `orr`)')
    for i, o, rd, rn, v in dp:
        if v == 0xFF00:
            print('     0x%08X  %s' % (base + i, disarm.arm(
                struct.unpack_from('<I', data, i)[0], base + i)))

    print('\n   * every `lsl #20` immediately followed by `lsr #20` '
          '(the twelve-bit mask)')
    byoff = {i: (t, a) for i, t, a, _rd, _rm in sh}
    for i, t, a, rd, rm in sh:
        if t == 0 and a == 20 and byoff.get(i + 4, (None, None))[:2] == (1, 20):
            print('     0x%08X' % (base + i))
            show(data, base, i, 8, pre=2)

    print('\n   * every `add #19`, both instruction sets')
    for i, o, rd, rn, v in dp:
        if o == 4 and v == 19:
            print('     ARM   0x%08X  %s' % (base + i, disarm.arm(
                struct.unpack_from('<I', data, i)[0], base + i)))
    for i, o, rd, v in timm:
        if o == 2 and v == 19:
            w = struct.unpack_from('<I', data, i & ~3)[0]
            print('     THUMB 0x%08X  add r%d,#19 -- containing ARM word '
                  '0x%08X  %s' % (base + i, rd, w, disarm.arm(w, base + (i & ~3))))

    print(TRIG_HEAD)
    vals = []
    i = 0
    while i < len(data) - 12:
        w = struct.unpack_from('<I', data, i)[0]
        nx = struct.unpack_from('<I', data, i + 4)[0]
        neg = (nx == 0xE2600000
               and struct.unpack_from('<I', data, i + 8)[0] == 0xE12FFF1E)
        if not neg and nx != 0xE12FFF1E:
            i += 4
            continue
        if (w & 0xFFFFF000) == 0xE3A00000:
            v = ring_sites.ror32(w & 0xFF, ((w >> 8) & 0xF) * 2)
        elif (w & 0xFFFFF000) == 0xE59F0000:
            t = i + 8 + (w & 0xFFF)
            if t + 4 > len(data):
                i += 4
                continue
            v = struct.unpack_from('<i', data, t)[0]
        else:
            i += 4
            continue
        vals.append((i, -v if neg else v))
        i += 12 if neg else 8
    print('     %d constant-returning stubs in the image' % len(vals))
    if vals:
        seq = [v for _, v in vals]
        k = 0
        while (k < len(seq)
               and abs(seq[k] - round(4096 * math.cos(math.radians(k)))) <= 1):
            k += 1
        print('     the first %d are round(4096 * cos(theta)) for theta = '
              '0..%d degrees, to within one' % (k, k - 1))
        print('     first twelve: %s' % ', '.join(str(x) for x in seq[:12]))
        print('     round(4096 * cos 5deg) = %d -- which is the 4080'
              % round(4096 * math.cos(math.radians(5))))
        for a, v in vals:
            if abs(v) == 4080:
                print('       0x%08X returns %d' % (base + a, v))
    print()

    print('\n   * every `and #15` within eight instructions of an ARM `lsr #4`')
    lsr4 = set(i for i, t, a, _rd, _rm in sh if t == 1 and a == 4)
    for i, o, rd, rn, v in dp:
        if o == 0 and v == 15 and any(abs(i - j) <= 32 for j in lsr4):
            print('     0x%08X' % (base + i))
            show(data, base, i, 6, pre=2)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
