#!/usr/bin/env python3
"""The codec's structure, when the constant scan has already come back empty.

Section 7, step 3 of the Java variant: stop relying on the constant, because a
constant can be computed.  Look for what a compiler cannot rewrite away -- the
4,096-byte ring, the mask, the control-register refill, the nibble split, and
the run escape's `+3` and `+19`.  These are section 3's fingerprints in
another encoding.

On ARM the encoding matters, and it cuts both ways:

  * `orr rX, rX, #0xFF00` **is** encodable (0xFF ror #24), so the control
    refill would appear as a plain immediate and this scan would see it.
  * `and rX, rY, #0x0FFF` is **not** encodable -- 4095 needs twelve bits.  A
    compiler masks to twelve bits with `lsl #20` / `lsr #20`, or loads 4095
    from the literal pool.  All three forms are counted.
  * `4096` **is** encodable (1 ror #20), so a 4,096-byte stack frame or an
    allocation argument is visible as an immediate.
  * `+3` and `+19` are ordinary small immediates and are noise on their own.
    They are only reported where they occur *together* inside one routine, and
    the count of each on its own is printed as the denominator.

Every count comes with the number of instructions it was drawn from, because
a zero means nothing without one.

    python struct_probe.py FILE [--base VA] [--window 200]

Standard library only.
"""

import struct
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
from ring_sites import ror32, ARM_DP


def arm_dp(data):
    """Yield (offset, opcode, rd, rn, value) for every ARM DP-immediate."""
    for i in range(0, len(data) - 3, 4):
        w = struct.unpack_from('<I', data, i)[0]
        if (w >> 28) == 0xF:
            continue
        if (w >> 26) & 3 or not (w >> 25) & 1:
            continue
        opc = (w >> 21) & 0xF
        if 8 <= opc <= 11 and not (w >> 20) & 1:
            continue
        yield (i, opc, (w >> 12) & 0xF, (w >> 16) & 0xF,
               ror32(w & 0xFF, ((w >> 8) & 0xF) * 2))


def arm_shifts(data):
    """Yield (offset, type, amount, rd, rm) for every ARM register shift."""
    for i in range(0, len(data) - 3, 4):
        w = struct.unpack_from('<I', data, i)[0]
        if (w >> 28) == 0xF:
            continue
        if (w >> 26) & 3 or (w >> 25) & 1 or (w >> 4) & 1:
            continue
        opc = (w >> 21) & 0xF
        if opc != 13:                       # mov only -- the shift idiom
            continue
        yield (i, (w >> 5) & 3, (w >> 7) & 0x1F, (w >> 12) & 0xF, w & 0xF)


def thumb_imm(data):
    """Yield (offset, op, rd, imm8) for THUMB mov/cmp/add/sub #imm8.

    This build is mostly THUMB -- there are seventeen times as many THUMB
    shifts as ARM ones -- so a probe that looked only at ARM would be looking
    at the wrong instruction set."""
    for i in range(0, len(data) - 1, 2):
        h = struct.unpack_from('<H', data, i)[0]
        if (h >> 13) != 1:
            continue
        yield (i, (h >> 11) & 3, (h >> 8) & 7, h & 0xFF)


def thumb_shifts(data):
    """Yield (offset, type, amount) for every THUMB lsl/lsr/asr immediate."""
    for i in range(0, len(data) - 1, 2):
        h = struct.unpack_from('<H', data, i)[0]
        if (h >> 13) != 0:
            continue
        t = (h >> 11) & 3
        if t == 3:
            continue
        yield (i, t, (h >> 6) & 0x1F)


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    path = argv[1]
    data = open(path, 'rb').read()
    base = int(argv[argv.index('--base') + 1], 0) if '--base' in argv else 0
    win = int(argv[argv.index('--window') + 1], 0) if '--window' in argv else 200

    dp = list(arm_dp(data))
    sh = list(arm_shifts(data))
    tsh = list(thumb_shifts(data))
    words = len(data) // 4
    lit = {}
    for i in range(0, len(data) - 3, 4):
        lit.setdefault(struct.unpack_from('<I', data, i)[0], []).append(i)

    print('%s' % path)
    print('  %d bytes, %d aligned words, load address 0x%08X'
          % (len(data), words, base))
    print('  %d ARM data-processing immediates, %d ARM mov-shifts, '
          '%d THUMB shifts' % (len(dp), len(sh), len(tsh)))
    print()

    def imm_sites(v):
        return [(i, o) for i, o, _rd, _rn, val in dp if val == v]

    print('  1. the control-register refill, `flags = byte | 0xFF00`')
    orr = [(i, o) for i, o, _rd, _rn, v in dp if v == 0xFF00 and o == 12]
    anyv = imm_sites(0xFF00)
    print('     %d immediates equal to 0xFF00, of which %d are `orr`'
          % (len(anyv), len(orr)))
    for i, o in orr[:20]:
        print('       0x%08X  %s' % (base + i, ARM_DP[o]))
    print()

    print('  2. the ring mask, `& 0x0FFF`')
    print('     4095 is not encodable as an ARM immediate, so it has three')
    print('     possible forms; all three are counted.')
    and4095 = [(i, o) for i, o, _rd, _rn, v in dp if v == 4095]
    print('     %d `and`-with-4095 immediates (expected 0 -- not encodable)'
          % len(and4095))
    print('     %d literal-pool words equal to 4095' % len(lit.get(4095, [])))
    pairs = []
    byoff = {i: (t, a, rd, rm) for i, t, a, rd, rm in sh}
    for i, t, a, rd, rm in sh:
        if t == 0 and a == 20 and (i + 4) in byoff:
            t2, a2, rd2, rm2 = byoff[i + 4]
            if t2 == 1 and a2 == 20:
                pairs.append(i)
    tpairs = []
    tby = {i: (t, a) for i, t, a in tsh}
    for i, t, a in tsh:
        if t == 0 and a == 20 and (i + 2) in tby and tby[i + 2] == (1, 20):
            tpairs.append(i)
    print('     %d ARM `lsl #20` immediately followed by `lsr #20`' % len(pairs))
    print('     %d THUMB `lsl #20` immediately followed by `lsr #20`'
          % len(tpairs))
    nib = [i for i, t, a in tsh
           if t == 0 and a == 28 and tby.get(i + 2) == (1, 28)]
    print('     (and %d THUMB `lsl #28`/`lsr #28` pairs, the four-bit mask)'
          % len(nib))
    for i in (pairs + tpairs)[:20]:
        print('       0x%08X' % (base + i))
    print()

    print('  3. a 4,096-byte ring')
    a4096 = imm_sites(4096)
    frames = [(i, o, v) for i, o, _rd, rn, v in dp
              if o in (2, 4) and rn == 13 and 4096 <= v <= 4400]
    print('     %d immediates equal to 4096, out of %d' % (len(a4096), len(dp)))
    print('     %d `add`/`sub` on sp with a 4096..4400 immediate '
          '(a ring on the stack)' % len(frames))
    for i, o, v in frames[:20]:
        print('       0x%08X  %s sp, #%d' % (base + i, ARM_DP[o], v))
    print()

    print('  4. the nibble split, `>> 4` next to `& 0x0F`')
    and15 = set(i for i, o, _rd, _rn, v in dp if v == 15 and o == 0)
    lsr4 = set(i for i, t, a, _rd, _rm in sh if t == 1 and a == 4)
    tlsr4 = set(i for i, t, a in tsh if t == 1 and a == 4)
    near = [i for i in and15 if any(abs(i - j) <= 32 for j in lsr4)]
    print('     %d `and #15`, %d ARM `lsr #4`, %d THUMB `lsr #4`'
          % (len(and15), len(lsr4), len(tlsr4)))
    print('     %d `and #15` within eight instructions of an ARM `lsr #4`'
          % len(near))
    print()

    print('  5. the run escape, `+3` and `+19`')
    timm = list(thumb_imm(data))
    add3 = sorted([i for i, o, _rd, _rn, v in dp if v == 3 and o == 4]
                  + [i for i, o, _rd, v in timm if o == 2 and v == 3])
    add19 = sorted([i for i, o, _rd, _rn, v in dp if v == 19 and o == 4]
                   + [i for i, o, _rd, v in timm if o == 2 and v == 19])
    print('     %d THUMB mov/cmp/add/sub #imm8 instructions as well' % len(timm))
    print('     %d `add #3`, %d `add #19`, both instruction sets'
          % (len(add3), len(add19)))
    both = [(a, b) for a in add19 for b in add3 if abs(a - b) <= win * 4]
    print('     %d pairs within %d instructions of each other' % (len(both), win))
    for a, b in both[:20]:
        print('       add #19 at 0x%08X, add #3 at 0x%08X' % (base + a, base + b))
    print()

    print('  6. all five together')
    print('     A routine implementing this format has the mask, the refill,')
    print('     the nibble split and both run constants inside a few hundred')
    print('     instructions of each other.  Sites where at least three of the')
    print('     five land within %d instructions:' % win)
    marks = ([('mask', i) for i in pairs + tpairs]
             + [('refill', i) for i, _ in orr]
             + [('nibble', i) for i in near]
             + [('+3', i) for i in add3]
             + [('+19', i) for i in add19]
             + [('ring', i) for i, _, _ in frames])
    marks.sort(key=lambda m: m[1])
    found = 0
    for k in range(len(marks)):
        grp = [m for m in marks if 0 <= m[1] - marks[k][1] <= win * 4]
        kinds = set(x[0] for x in grp)
        if len(kinds) >= 3 and '+3' in kinds and len(kinds - {'+3', '+19'}) >= 1:
            print('       0x%08X  %s' % (base + marks[k][1],
                                         ', '.join(sorted(kinds))))
            found += 1
            if found > 30:
                print('       ... (truncated)')
                break
    if not found:
        print('       none.')


if __name__ == '__main__':
    main(sys.argv)
