#!/usr/bin/env python3
"""Is the platform's own LZ77 *format* decoded by code in this image?

`bios_calls.py` answers a different question -- whether the BIOS service is
called -- and on this cartridge it answers no, twelve wrappers and not one
caller.  But `ndscomp.py --census` says 102 files *are* BIOS `LZ77` streams
that decode and consume themselves exactly.  Something reads them, and if it
is not the BIOS then the code is in the image.

So this looks for the format's arithmetic rather than for the service.  A
decoder of the BIOS `LZ77` stream has to compute, for every two-byte token:

    length       = (b0 >> 4) + 3
    displacement = (((b0 & 0x0F) << 8) | b1) + 1

and neither half is optional -- a compiler can reorder them, keep them in
different registers or unroll the copy, but it cannot make the nibble split
or the twelve-bit assembly go away.  Four fingerprints are counted, in both
instruction sets, each with the number of instructions it was drawn from:

  1. the length nibble     ARM `mov rD, rS, lsr #4`; THUMB `lsr rD, rS, #4`
  2. the `+3`              ARM `add rD, rS, #3`; THUMB `add rD, #3` and
                           `add rD, rS, #3` (the imm3 form, which is the one
                           a compiler usually picks and the one a probe
                           written for the imm8 form misses)
  3. the low nibble        ARM `and rD, rS, #15`; THUMB `mov rT,#15` + `and`,
                           or the shift-pair `lsl #28` / `lsr #28`
  4. the twelve-bit join   ARM `orr`/`add` with `lsl #8`; THUMB `lsl rD,rS,#8`

and then the co-locations, because any one of them alone is noise: a window
in which the length nibble and the `+3` both appear, and a window in which
the low nibble and the join both appear.

Two further shapes are counted because a decoder need not split the token
into nibbles at all.  One that assembles the two bytes into a halfword first
gets the length with `lsr #12` and the displacement with `& 0x0FFF`; and one
whose copy loop is a `do/while` carries `+2` or `+1` where the arithmetic
form carries `+3`.  Both variants are scanned, and the wrapper addresses are
searched for as **data words** as well, because a call through a function
pointer would leave one there and would leave no branch for `bios_calls.py`
to resolve.

    python lzprobe.py FILE [--base VA] [--window 40]

Standard library only.
"""

import struct
import sys


def arm_dp(w):
    """(kind, opcode, operand) for an ARM data-processing word, else None."""
    if (w >> 28) == 0xF or ((w >> 26) & 3):
        return None
    op = (w >> 21) & 0xF
    if (w >> 25) & 1:
        rot = ((w >> 8) & 0xF) * 2
        v = w & 0xFF
        return ('imm', op, ((v >> rot) | (v << (32 - rot))) & 0xFFFFFFFF
                if rot else v)
    return ('reg', op, ((w >> 7) & 0x1F, (w >> 5) & 3))


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    path = argv[1]
    base = int(argv[argv.index('--base') + 1], 0) if '--base' in argv else 0
    win = int(argv[argv.index('--window') + 1], 0) if '--window' in argv else 40
    d = open(path, 'rb').read()

    words = [struct.unpack_from('<I', d, i)[0] for i in range(0, len(d) - 3, 4)]
    halves = [struct.unpack_from('<H', d, i)[0] for i in range(0, len(d) - 1, 2)]
    dps = [arm_dp(w) for w in words]

    a_lsr4 = [i for i, p in enumerate(dps)
              if p and p[0] == 'reg' and p[2] == (4, 1)]
    a_add3 = [i for i, p in enumerate(dps)
              if p and p[0] == 'imm' and p[1] == 4 and p[2] == 3]
    a_and15 = [i for i, p in enumerate(dps)
               if p and p[0] == 'imm' and p[1] == 0 and p[2] == 15]
    a_join = [i for i, p in enumerate(dps)
              if p and p[0] == 'reg' and p[1] in (12, 4) and p[2] == (8, 0)]

    def t_lsr4(h):
        return (h & 0xF800) == 0x0800 and ((h >> 6) & 0x1F) == 4

    def t_add3(h):
        return (((h & 0xFE00) == 0x1C00 and ((h >> 6) & 7) == 3) or
                ((h & 0xF800) == 0x3000 and (h & 0xFF) == 3))

    def t_lsl8(h):
        return (h & 0xF800) == 0x0000 and ((h >> 6) & 0x1F) == 8

    def t_mov15(h):
        return (h & 0xF800) == 0x2000 and (h & 0xFF) == 15

    t_l4 = [i for i, h in enumerate(halves) if t_lsr4(h)]
    t_a3 = [i for i, h in enumerate(halves) if t_add3(h)]
    t_m15 = [i for i, h in enumerate(halves) if t_mov15(h)]
    t_l8 = [i for i, h in enumerate(halves) if t_lsl8(h)]
    t_n4 = [i for i in range(len(halves) - 1)
            if (halves[i] & 0xF800) == 0x0000 and ((halves[i] >> 6) & 0x1F) == 28
            and (halves[i + 1] & 0xF800) == 0x0800
            and ((halves[i + 1] >> 6) & 0x1F) == 28]

    print(path)
    print('  %d bytes, load address 0x%08X, window %d instructions'
          % (len(d), base, win))
    print('  %d aligned words, %d halfwords' % (len(words), len(halves)))
    print()
    print('  ARM')
    print('    %7d data-processing words with an immediate operand'
          % sum(1 for p in dps if p and p[0] == 'imm'))
    print('    %7d  1. mov rD, rS, lsr #4      (the length nibble)' % len(a_lsr4))
    print('    %7d  2. add rD, rS, #3          (the +3)' % len(a_add3))
    print('    %7d  3. and rD, rS, #15         (the low nibble)' % len(a_and15))
    print('    %7d  4. orr/add ..., lsl #8     (the twelve-bit join)' % len(a_join))
    print('  THUMB')
    print('    %7d halfwords decoded' % len(halves))
    print('    %7d  1. lsr rD, rS, #4' % len(t_l4))
    print('    %7d  2. add #3, either form' % len(t_a3))
    print('    %7d  3. mov #15, and %d lsl #28 / lsr #28 pairs'
          % (len(t_m15), len(t_n4)))
    print('    %7d  4. lsl rD, rS, #8' % len(t_l8))
    print()

    def near(xs, ys, step, label):
        ys = set(ys)
        hits = [x for x in xs
                if any(x + k in ys for k in range(-win, win + 1) if k)]
        print('  %s: %d' % (label, len(hits)))
        for x in hits[:20]:
            print('      0x%08X' % (base + x * step))
        return hits

    print('  co-locations, within %d instructions either way' % win)
    near(a_lsr4, a_add3, 4, 'ARM   length nibble with a +3')
    near(a_and15, a_join, 4, 'ARM   low nibble with a twelve-bit join')
    near(t_l4, t_a3, 2, 'THUMB length nibble with a +3')
    near(t_m15 + t_n4, t_l8, 2, 'THUMB low nibble with a twelve-bit join')
    print()

    # The halfword-token variant: length from `lsr #12`, displacement from a
    # twelve-bit mask, and no nibble anywhere.
    a_l12 = [i for i, p in enumerate(dps)
             if p and p[0] == 'reg' and p[2] == (12, 1)]
    t_l12 = [i for i, h in enumerate(halves)
             if (h & 0xF800) == 0x0800 and ((h >> 6) & 0x1F) == 12]
    print('  the halfword-token variant, length from bits 15..12')
    print('    %7d ARM   mov rD, rS, lsr #12' % len(a_l12))
    print('    %7d THUMB lsr rD, rS, #12' % len(t_l12))
    near(a_l12, a_add3, 4, 'ARM   lsr #12 with a +3')
    near(t_l12, t_a3, 2, 'THUMB lsr #12 with a +3')
    print()

    # The do/while variant: the +3 becomes a +2 or a +1.
    print('  the do/while variant, where the +3 is carried as +2 or +1')
    for v in (1, 2):
        av = set(i for i, p in enumerate(dps)
                 if p and p[0] == 'imm' and p[1] in (2, 4) and p[2] == v)
        tv = set(i for i, h in enumerate(halves)
                 if ((h & 0xFE00) in (0x1C00, 0x1E00) and ((h >> 6) & 7) == v)
                 or ((h & 0xF800) in (0x3000, 0x3800) and (h & 0xFF) == v))
        na = sum(1 for i in a_lsr4
                 if any(i + k in av for k in range(-win, win + 1) if k))
        nt = sum(1 for i in t_l4
                 if any(i + k in tv for k in range(-win, win + 1) if k))
        print('    length nibble within %d of a +/-%d:  ARM %d, THUMB %d'
              % (win, v, na, nt))


if __name__ == '__main__':
    main(sys.argv)
