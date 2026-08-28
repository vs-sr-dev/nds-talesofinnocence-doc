#!/usr/bin/env python3
"""A small ARMv5TE / THUMB disassembler, enough to read a routine.

The corpus already carries `dismips.py` and `disppc.py` for the same job on
the two machines it had met before.  This is the ARM one.  It covers what a
compiler emits -- data processing, loads and stores, multiplies, block
transfers, branches, the THUMB subset -- and prints `.word` for anything it
does not know rather than guessing, so a literal pool reads as a literal pool.

    python disarm.py FILE OFFSET COUNT [--base VA] [--thumb]

OFFSET is a file offset; --base gives the load address so the printed
addresses match the ones `ring_sites.py` reports.

Standard library only.
"""

import struct
import sys

COND = ['eq', 'ne', 'cs', 'cc', 'mi', 'pl', 'vs', 'vc',
        'hi', 'ls', 'ge', 'lt', 'gt', 'le', '', 'nv']
DP = ['and', 'eor', 'sub', 'rsb', 'add', 'adc', 'sbc', 'rsc',
      'tst', 'teq', 'cmp', 'cmn', 'orr', 'mov', 'bic', 'mvn']
SHIFT = ['lsl', 'lsr', 'asr', 'ror']
REG = ['r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7',
       'r8', 'r9', 'r10', 'r11', 'r12', 'sp', 'lr', 'pc']


def ror32(v, n):
    n &= 31
    return ((v >> n) | (v << (32 - n))) & 0xFFFFFFFF


def reglist(mask):
    out, i = [], 0
    while i < 16:
        if mask & (1 << i):
            j = i
            while j + 1 < 16 and mask & (1 << (j + 1)):
                j += 1
            out.append(REG[i] if i == j else '%s-%s' % (REG[i], REG[j]))
            i = j
        i += 1
    return '{%s}' % ','.join(out)


def shifted(w):
    rm = REG[w & 0xF]
    typ = (w >> 5) & 3
    if (w >> 4) & 1:
        return '%s,%s %s' % (rm, SHIFT[typ], REG[(w >> 8) & 0xF])
    amt = (w >> 7) & 0x1F
    if amt == 0:
        if typ == 0:
            return rm
        if typ == 3:
            return '%s,rrx' % rm
        amt = 32
    return '%s,%s #%d' % (rm, SHIFT[typ], amt)


def arm(w, addr):
    c = COND[w >> 28]
    if (w >> 28) == 0xF:
        if (w & 0xFE000000) == 0xFA000000:
            off = w & 0x00FFFFFF
            off = off - 0x1000000 if off & 0x800000 else off
            return 'blx     0x%08X' % (addr + 8 + off * 4 + ((w >> 24) & 1) * 2)
        return '.word   0x%08X' % w
    op = (w >> 25) & 7
    if (w & 0x0FFFFFF0) == 0x012FFF10:
        return 'bx%-6s%s' % (c, REG[w & 0xF])
    if (w & 0x0FFFFFF0) == 0x012FFF30:
        return 'blx%-5s%s' % (c, REG[w & 0xF])
    if (w & 0x0FC000F0) == 0x00000090:                      # mul / mla
        rd, rn, rs, rm = (w >> 16) & 0xF, (w >> 12) & 0xF, (w >> 8) & 0xF, w & 0xF
        if (w >> 21) & 1:
            return 'mla%s%-3s%s,%s,%s,%s' % (c, 's' if w & 0x100000 else '',
                                             REG[rd], REG[rm], REG[rs], REG[rn])
        return 'mul%s%-3s%s,%s,%s' % (c, 's' if w & 0x100000 else '',
                                      REG[rd], REG[rm], REG[rs])
    if (w & 0x0F8000F0) == 0x00800090:                      # long multiply
        return 'smull/umull %s' % REG[(w >> 16) & 0xF]
    if (w & 0x0E400F90) == 0x00000090:                      # ldrh/strh reg
        pass
    if (w & 0x0E000090) == 0x00000090 and ((w >> 5) & 3):   # halfword / signed
        rd, rn = (w >> 12) & 0xF, (w >> 16) & 0xF
        ld = 'ldr' if (w >> 20) & 1 else 'str'
        kind = {1: 'h', 2: 'sb', 3: 'sh'}[(w >> 5) & 3]
        if (w >> 22) & 1:
            imm = ((w >> 4) & 0xF0) | (w & 0xF)
            o = ',#%s%d' % ('' if (w >> 23) & 1 else '-', imm) if imm else ''
        else:
            o = ',%s%s' % ('' if (w >> 23) & 1 else '-', REG[w & 0xF])
        return '%s%s%-4s%s,[%s%s]%s' % (ld, c, kind, REG[rd], REG[rn], o,
                                        '!' if (w >> 21) & 1 else '')
    if op in (0, 1):                                        # data processing
        opc = (w >> 21) & 0xF
        s = (w >> 20) & 1
        rd, rn = (w >> 12) & 0xF, (w >> 16) & 0xF
        if 8 <= opc <= 11 and not s:
            return 'msr/mrs 0x%08X' % w
        if op == 1:
            val = ror32(w & 0xFF, ((w >> 8) & 0xF) * 2)
            src = '#%d' % val if val < 0x10000 else '#0x%X' % val
        else:
            src = shifted(w)
        m = DP[opc] + c + ('s' if s and opc not in range(8, 12) else '')
        if opc in (13, 15):
            return '%-8s%s,%s' % (m, REG[rd], src)
        if 8 <= opc <= 11:
            return '%-8s%s,%s' % (m, REG[rn], src)
        return '%-8s%s,%s,%s' % (m, REG[rd], REG[rn], src)
    if op in (2, 3):                                        # load/store
        rd, rn = (w >> 12) & 0xF, (w >> 16) & 0xF
        ld = 'ldr' if (w >> 20) & 1 else 'str'
        b = 'b' if (w >> 22) & 1 else ''
        u = '' if (w >> 23) & 1 else '-'
        if op == 2:
            imm = w & 0xFFF
            if rn == 15 and (w >> 24) & 1:
                tgt = addr + 8 + (imm if u == '' else -imm)
                return '%s%s%-4s%s,[pc,#%s%d]   ; 0x%08X' % (ld, c, b, REG[rd],
                                                            u, imm, tgt)
            o = ',#%s%d' % (u, imm) if imm else ''
        else:
            o = ',%s%s' % (u, shifted(w))
        if (w >> 24) & 1:
            return '%s%s%-4s%s,[%s%s]%s' % (ld, c, b, REG[rd], REG[rn], o,
                                            '!' if (w >> 21) & 1 else '')
        return '%s%s%-4s%s,[%s]%s' % (ld, c, b, REG[rd], REG[rn], o)
    if op == 4:                                             # block transfer
        ld = 'ldm' if (w >> 20) & 1 else 'stm'
        p, u = (w >> 24) & 1, (w >> 23) & 1
        mode = {(1, 1): 'ib', (0, 1): 'ia', (1, 0): 'db', (0, 0): 'da'}[(p, u)]
        if REG[(w >> 16) & 0xF] == 'sp':
            mode = {'db': 'fd', 'ia': 'fd', 'ib': 'fa', 'da': 'ea'}[mode] \
                if not (w >> 20) & 1 else {'ia': 'fd', 'db': 'ea', 'ib': 'ed',
                                           'da': 'fa'}[mode]
        return '%s%s%-3s%s%s,%s%s' % (ld, c, mode, REG[(w >> 16) & 0xF],
                                      '!' if (w >> 21) & 1 else '',
                                      reglist(w & 0xFFFF),
                                      '^' if (w >> 22) & 1 else '')
    if op == 5:                                             # branch
        off = w & 0x00FFFFFF
        off = off - 0x1000000 if off & 0x800000 else off
        return '%s%-7s0x%08X' % ('bl' if (w >> 24) & 1 else 'b', c,
                                 addr + 8 + off * 4)
    if op == 7 and (w >> 24) & 1:
        return 'svc%-5s0x%06X' % (c, w & 0xFFFFFF)
    return '.word   0x%08X' % w


def thumb(h, addr, nxt=None):
    top = h >> 12
    if (h >> 11) == 0b00011:
        opn = 'sub' if (h >> 9) & 1 else 'add'
        if (h >> 10) & 1:
            return '%-8s%s,%s,#%d' % (opn, REG[h & 7], REG[(h >> 3) & 7], (h >> 6) & 7)
        return '%-8s%s,%s,%s' % (opn, REG[h & 7], REG[(h >> 3) & 7], REG[(h >> 6) & 7])
    if (h >> 13) == 0:
        return '%-8s%s,%s,#%d' % (SHIFT[(h >> 11) & 3], REG[h & 7],
                                  REG[(h >> 3) & 7], (h >> 6) & 0x1F)
    if (h >> 13) == 1:
        return '%-8s%s,#%d' % (['mov', 'cmp', 'add', 'sub'][(h >> 11) & 3],
                               REG[(h >> 8) & 7], h & 0xFF)
    if (h >> 10) == 0b010000:
        ops = ['and', 'eor', 'lsl', 'lsr', 'asr', 'adc', 'sbc', 'ror',
               'tst', 'neg', 'cmp', 'cmn', 'orr', 'mul', 'bic', 'mvn']
        return '%-8s%s,%s' % (ops[(h >> 6) & 0xF], REG[h & 7], REG[(h >> 3) & 7])
    if (h >> 10) == 0b010001:
        o = (h >> 8) & 3
        rd = (h & 7) | ((h >> 4) & 8)
        rm = (h >> 3) & 0xF
        if o == 3:
            return '%-8s%s' % ('blx' if h & 0x80 else 'bx', REG[rm])
        return '%-8s%s,%s' % (['add', 'cmp', 'mov'][o], REG[rd], REG[rm])
    if (h >> 11) == 0b01001:
        tgt = ((addr + 4) & ~3) + (h & 0xFF) * 4
        return 'ldr     %s,[pc,#%d]   ; 0x%08X' % (REG[(h >> 8) & 7],
                                                   (h & 0xFF) * 4, tgt)
    if top in (5,):
        ops = ['str', 'strh', 'strb', 'ldrsb', 'ldr', 'ldrh', 'ldrb', 'ldrsh']
        return '%-8s%s,[%s,%s]' % (ops[(h >> 9) & 7], REG[h & 7],
                                   REG[(h >> 3) & 7], REG[(h >> 6) & 7])
    if top in (6, 7, 8):
        ld = 'ldr' if (h >> 11) & 1 else 'str'
        if top == 8:
            ld += 'h'
            sc = 2
        elif top == 7:
            ld += 'b'
            sc = 1
        else:
            sc = 4
        return '%-8s%s,[%s,#%d]' % (ld, REG[h & 7], REG[(h >> 3) & 7],
                                    ((h >> 6) & 0x1F) * sc)
    if top == 9:
        return '%-8s%s,[sp,#%d]' % ('ldr' if (h >> 11) & 1 else 'str',
                                    REG[(h >> 8) & 7], (h & 0xFF) * 4)
    if top == 0xA:
        return 'add     %s,%s,#%d' % (REG[(h >> 8) & 7],
                                      'pc' if not (h >> 11) & 1 else 'sp',
                                      (h & 0xFF) * 4)
    if (h >> 8) == 0b10110000:
        return '%-8ssp,#%d' % ('sub' if h & 0x80 else 'add', (h & 0x7F) * 4)
    if (h >> 9) & 0x3F in (0b1011010, 0b1011110):
        push = not (h >> 11) & 1
        extra = 0x4000 if (push and h & 0x100) else (0x8000 if (not push and h & 0x100) else 0)
        return '%-8s%s' % ('push' if push else 'pop', reglist((h & 0xFF) | extra))
    if top == 0xC:
        return '%-8s%s!,%s' % ('ldmia' if (h >> 11) & 1 else 'stmia',
                               REG[(h >> 8) & 7], reglist(h & 0xFF))
    if top == 0xD:
        c = (h >> 8) & 0xF
        if c == 0xF:
            return 'svc     0x%02X' % (h & 0xFF)
        off = h & 0xFF
        off = off - 256 if off & 0x80 else off
        return 'b%-7s0x%08X' % (COND[c], addr + 4 + off * 2)
    if (h >> 11) == 0b11100:
        off = h & 0x7FF
        off = off - 0x800 if off & 0x400 else off
        return 'b       0x%08X' % (addr + 4 + off * 2)
    if (h >> 11) == 0b11110 and nxt is not None and (nxt >> 11) in (0b11111, 0b11101):
        hi = h & 0x7FF
        hi = hi - 0x800 if hi & 0x400 else hi
        tgt = addr + 4 + (hi << 12) + (nxt & 0x7FF) * 2
        return '%-8s0x%08X' % ('bl' if (nxt >> 11) == 0b11111 else 'blx', tgt)
    return '.hword  0x%04X' % h


def disasm(data, off, count, base=0, is_thumb=False):
    out = []
    if is_thumb:
        i = 0
        while i < count * 2 and off + i + 1 < len(data):
            h = struct.unpack_from('<H', data, off + i)[0]
            n = struct.unpack_from('<H', data, off + i + 2)[0] \
                if off + i + 3 < len(data) else None
            txt = thumb(h, base + off + i, n)
            wide = txt.startswith('bl ') or txt.startswith('bl  ') or txt.startswith('blx     0x')
            out.append('%08X  %04X       %s' % (base + off + i, h, txt))
            i += 4 if wide else 2
    else:
        for k in range(count):
            a = off + k * 4
            if a + 3 >= len(data):
                break
            w = struct.unpack_from('<I', data, a)[0]
            out.append('%08X  %08X   %s' % (base + a, w, arm(w, base + a)))
    return out


def main(argv):
    if len(argv) < 4:
        raise SystemExit(__doc__)
    data = open(argv[1], 'rb').read()
    off = int(argv[2], 0)
    count = int(argv[3], 0)
    base = int(argv[argv.index('--base') + 1], 0) if '--base' in argv else 0
    for line in disasm(data, off, count, base, '--thumb' in argv):
        print(line)


if __name__ == '__main__':
    main(sys.argv)
