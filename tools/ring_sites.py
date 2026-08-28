#!/usr/bin/env python3
"""Find the block codec's ring constants in an executable, on four CPUs.

Section 7 of tales-blockcodec-doc gives the shortcut: scan for the immediates
4078 and 4079 (and, since 2004, 4080; and, since the tenth build, 4070 and
4071, which are the bound of a ring clear unrolled by eight).  They are the
packer's constants, not the programmer's, and nothing else in a game has a
reason to load 4,078.  It works in the negative too: an executable with no
4078 anywhere does not contain the decoder.

The shortcut was written for MIPS and extended to PowerPC.  Both are
fixed-width machines with a 16-bit immediate field, so "scan the words" is a
complete search.  **On ARM it is not**, and that is the reason this file
exists:

  * An ARM data-processing immediate is an 8-bit value rotated right by an
    even amount.  **4078 (0xFEE) and 4079 (0xFEF) cannot be encoded at all**
    -- they need nine significant bits.  A compiler emits them as 32-bit words
    in the literal pool, loaded with `ldr rX, [pc, #off]`.
  * **4080 (0xFF0) can** be encoded: 0xFF ror 28.  So the three constants of
    the corpus behave in two different ways on this machine, which is itself a
    datum about what a hit means.
  * 4070 (0xFE6) and 4071 (0xFE7) cannot be encoded either.
  * In THUMB, `mov rd, #imm8` reaches 255 and no further, so every one of
    these constants is a literal-pool word there too.

So the ARM scan is two scans, and both are run and both denominators are
printed:

  1. **immediate fields** -- every ARM data-processing instruction with I=1,
     and every THUMB instruction carrying a literal, decoded and compared;
  2. **literal-pool words** -- every 4-byte-aligned u32 equal to a wanted
     constant, then cross-referenced against every PC-relative load in the
     image to say whether any instruction actually points at it.

A raw word match is weak on its own: a specific 32-bit value turns up by
chance about once per 4 GB of uniform random data, but code is not uniform and
small integers are common.  The cross-reference is what makes a hit mean
something, and the denominator is printed either way, because "zero hits" is
worth nothing without "out of how many words".

    python ring_sites.py FILE --arm  [--base VA] [--imm 4078,4079,4080]
    python ring_sites.py FILE --mips [--base VA --off FILEOFF]
    python ring_sites.py FILE --ppc  [--base VA --off FILEOFF]

Standard library only.
"""

import struct
import sys

# ---------------------------------------------------------------- MIPS / PPC

MIPS_IMM = {
    4: 'beq', 5: 'bne', 6: 'blez', 7: 'bgtz', 8: 'addi', 9: 'addiu',
    10: 'slti', 11: 'sltiu', 12: 'andi', 13: 'ori', 14: 'xori',
    15: 'lui', 24: 'daddi', 25: 'daddiu',
}
MIPS_SKIP = {4, 5, 6, 7, 15}

PPC_IMM = {
    7: 'mulli', 8: 'subfic', 10: 'cmplwi', 11: 'cmpwi', 12: 'addic',
    13: 'addic.', 14: 'addi', 15: 'addis', 24: 'ori', 25: 'oris',
    28: 'andi.', 29: 'andis.',
}
PPC_SKIP = {15, 25, 29}


def scan_fixed(data, arch, base, off, size, wanted):
    fmt = '<I' if arch == 'mips' else '>I'
    hits = []
    for i in range(0, size - 3, 4):
        w = struct.unpack_from(fmt, data, off + i)[0]
        imm = w & 0xFFFF
        if imm not in wanted:
            continue
        op = w >> 26
        if arch == 'mips':
            if op not in MIPS_IMM or op in MIPS_SKIP:
                continue
            name = MIPS_IMM[op]
        else:
            if op not in PPC_IMM or op in PPC_SKIP:
                continue
            name = PPC_IMM[op]
        hits.append((base + i, w, name, imm))
    return hits


# ---------------------------------------------------------------------- ARM

ARM_DP = ['and', 'eor', 'sub', 'rsb', 'add', 'adc', 'sbc', 'rsc',
          'tst', 'teq', 'cmp', 'cmn', 'orr', 'mov', 'bic', 'mvn']
COND = ['eq', 'ne', 'cs', 'cc', 'mi', 'pl', 'vs', 'vc',
        'hi', 'ls', 'ge', 'lt', 'gt', 'le', '', 'nv']


def ror32(v, n):
    n &= 31
    return ((v >> n) | (v << (32 - n))) & 0xFFFFFFFF


def arm_encodable(value):
    """Return (imm8, rot) if `value` fits an ARM data-processing immediate."""
    for rot in range(0, 32, 2):
        cand = ror32(value, 32 - rot) if rot else value
        # value == ror(imm8, rot)  <=>  imm8 == rol(value, rot)
        imm8 = ((value << rot) | (value >> (32 - rot))) & 0xFFFFFFFF if rot else value
        if imm8 <= 0xFF:
            return imm8, rot
    return None


def arm_immediates(data, base, wanted):
    """Every ARM data-processing instruction whose immediate is in `wanted`."""
    hits = []
    total = 0
    for i in range(0, len(data) - 3, 4):
        w = struct.unpack_from('<I', data, i)[0]
        if (w >> 28) == 0xF:                    # unconditional space
            continue
        if (w >> 26) & 3 or not (w >> 25) & 1:  # not a DP-immediate
            continue
        opc = (w >> 21) & 0xF
        s = (w >> 20) & 1
        if 8 <= opc <= 11 and not s:            # MSR / undefined
            continue
        total += 1
        rot = (w >> 8) & 0xF
        imm8 = w & 0xFF
        val = ror32(imm8, rot * 2)
        if val in wanted:
            rd, rn = (w >> 12) & 0xF, (w >> 16) & 0xF
            hits.append((base + i, w,
                         '%s%s r%d,r%d,#%d' % (ARM_DP[opc], COND[w >> 28], rd, rn, val),
                         val))
    return hits, total


def thumb_immediates(data, base, wanted):
    """Every THUMB instruction carrying a literal, decoded.

    `mov/cmp/add/sub rd,#imm8` reaches 255; `add/sub rd,rn,#imm3` reaches 7;
    `add sp,#imm7*4` reaches 508; the shifted forms carry a shift count, not a
    value.  None of them can hold a four-digit constant, which is the point.
    """
    hits = []
    total = 0
    for i in range(0, len(data) - 1, 2):
        h = struct.unpack_from('<H', data, i)[0]
        val = None
        if (h >> 13) == 0b001:                       # mov/cmp/add/sub imm8
            val = h & 0xFF
        elif (h >> 10) == 0b0001111 or (h >> 10) == 0b0001110:
            val = (h >> 6) & 7                       # add/sub imm3
        elif (h >> 8) == 0b10110000:                 # add/sub sp, #imm7*4
            val = (h & 0x7F) * 4
        if val is None:
            continue
        total += 1
        if val in wanted:
            hits.append((base + i, h, 'thumb #%d' % val, val))
    return hits, total


def pc_relative_targets(data, base):
    """Map every PC-relative load in the image to the address it reads.

    Both encodings, because a NitroSDK build is a mixture of the two:
      ARM    ldr rd,[pc,#+/-imm12]   target = (addr + 8) +/- imm12
      THUMB  ldr rd,[pc,#imm8*4]     target = ((addr + 4) & ~3) + imm8*4
    """
    targets = {}
    n_arm = n_thumb = 0
    for i in range(0, len(data) - 3, 4):
        w = struct.unpack_from('<I', data, i)[0]
        if (w >> 28) == 0xF:
            continue
        if (w >> 26) & 3 != 1:
            continue
        if (w >> 25) & 1:                 # register offset
            continue
        if not (w >> 24) & 1:             # post-indexed
            continue
        if (w >> 22) & 1:                 # byte
            continue
        if not (w >> 20) & 1:             # store
            continue
        if (w >> 16) & 0xF != 15:         # not PC-relative
            continue
        imm = w & 0xFFF
        t = base + i + 8 + (imm if (w >> 23) & 1 else -imm)
        targets.setdefault(t, []).append(('arm', base + i))
        n_arm += 1
    for i in range(0, len(data) - 1, 2):
        h = struct.unpack_from('<H', data, i)[0]
        if (h >> 11) != 0b01001:
            continue
        t = (((base + i + 4) & ~3) + (h & 0xFF) * 4)
        targets.setdefault(t, []).append(('thumb', base + i))
        n_thumb += 1
    return targets, n_arm, n_thumb


def literal_words(data, base, wanted, targets):
    hits = []
    total = 0
    for i in range(0, len(data) - 3, 4):
        total += 1
        w = struct.unpack_from('<I', data, i)[0]
        if w in wanted:
            hits.append((base + i, w, targets.get(base + i, [])))
    return hits, total


def arm_routine_start(data, base, va, limit=8192):
    """Walk back to something that looks like a function entry.

    `stmfd sp!, {...,lr}` is the ARM prologue an SDK build emits; `push {..,lr}`
    is the THUMB one.  Neither is guaranteed, so this is a hint, not a claim.
    """
    a = va
    for _ in range(limit // 4):
        a -= 4
        if a < base:
            return None
        w = struct.unpack_from('<I', data, a - base)[0]
        if (w & 0x0FFF0000) == 0x092D0000 and (w & 0x4000):    # stmfd sp!,{..lr}
            return a
    return None


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    path = argv[1]
    arch = ('arm' if '--arm' in argv else 'mips' if '--mips' in argv
            else 'ppc' if '--ppc' in argv else None)
    if arch is None:
        raise SystemExit('say --arm, --mips or --ppc')
    data = open(path, 'rb').read()
    base = int(argv[argv.index('--base') + 1], 0) if '--base' in argv else 0
    off = int(argv[argv.index('--off') + 1], 0) if '--off' in argv else 0
    size = len(data) - off
    if '--size' in argv:
        size = int(argv[argv.index('--size') + 1], 0)
    wanted = (4078, 4079)
    if '--imm' in argv:
        wanted = tuple(int(x, 0) for x in argv[argv.index('--imm') + 1].split(','))

    if arch != 'arm':
        hits = scan_fixed(data, arch, base, off, size, wanted)
        print('%s, %s, %d words scanned, looking for %s'
              % (path, arch, size // 4, '/'.join(str(x) for x in wanted)))
        if not hits:
            print('\nno %s immediate anywhere in this image.'
                  % ' or '.join(str(x) for x in wanted))
            return
        print('\n%-12s %-10s %-8s %6s' % ('ADDRESS', 'WORD', 'FORM', 'IMM'))
        for va, w, name, imm in hits:
            print('0x%08X   0x%08X %-8s %6d' % (va, w, name, imm))
        print('\n%d sites' % len(hits))
        return

    body = data[off:off + size]
    print('%s' % path)
    print('  %d bytes, load address 0x%08X, ARM/THUMB' % (len(body), base))
    print('  looking for %s' % ', '.join(str(x) for x in wanted))
    print()
    print('  encodability as an ARM data-processing immediate '
          '(8 bits rotated by an even amount):')
    for c in wanted:
        e = arm_encodable(c)
        if e:
            print('    %5d (0x%03X)  YES  0x%02X ror #%d'
                  % (c, c, e[0], e[1]))
        else:
            print('    %5d (0x%03X)  NO   -- must be a literal-pool word'
                  % (c, c))
    print()

    imm_hits, imm_total = arm_immediates(body, base, wanted)
    th_hits, th_total = thumb_immediates(body, base, wanted)
    targets, n_arm_ldr, n_thumb_ldr = pc_relative_targets(body, base)
    lit_hits, lit_total = literal_words(body, base, wanted, targets)

    print('  pass 1 -- immediate fields')
    print('    %8d ARM data-processing instructions with an immediate operand'
          % imm_total)
    print('    %8d THUMB instructions carrying a literal' % th_total)
    print('    %8d hits' % (len(imm_hits) + len(th_hits)))
    for va, w, name, val in imm_hits + th_hits:
        s = arm_routine_start(body, base, va)
        print('      0x%08X  0x%08X  %-28s  %s'
              % (va, w, name,
                 ('prologue 0x%08X (+%d words)' % (s, (va - s) // 4)) if s else '?'))
    print()
    print('  pass 2 -- 32-bit words in the literal pool')
    print('    %8d aligned words scanned' % lit_total)
    print('    %8d ARM + %d THUMB PC-relative loads, %d distinct targets'
          % (n_arm_ldr, n_thumb_ldr, len(targets)))
    print('    %8d hits' % len(lit_hits))
    for va, w, refs in lit_hits:
        if refs:
            r = ', '.join('%s ldr @0x%08X' % (k, a) for k, a in refs[:4])
        else:
            r = 'NOT the target of any PC-relative load in this image'
        print('      0x%08X  = %d  <- %s' % (va, w, r))
    print()
    if not (imm_hits or th_hits or lit_hits):
        print('  no %s anywhere in this image, in either encoding.'
              % ' or '.join(str(x) for x in wanted))
        print('  By section 7 of the codec specification that is evidence the')
        print('  decoder is not present, not merely that it was not found --')
        print('  and on ARM the literal-pool pass is the half that matters,')
        print('  because the two cursors cannot be encoded as immediates.')


if __name__ == '__main__':
    main(sys.argv)
