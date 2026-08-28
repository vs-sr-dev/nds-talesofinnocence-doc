#!/usr/bin/env python3
"""Which decompressor does the platform already provide, and does this build call it?

Section 7's rule for a non-console target: ask first what the machine hands you
for free, because that is what a small team will use.  On the Game Boy Advance
in 2003 the answer was the BIOS `LZ77UnComp` and `RLUnComp`.  The Nintendo DS
BIOS offers the same services through the same mechanism -- a `SWI` with the
service number in the instruction word -- so the question is answerable by
counting instructions rather than by argument.

This counts every `SWI` in an image, in both instruction sets, and names the
decompression services among them.

    python bios_calls.py FILE [--base VA] [--also FILE@VA ...]

`--also` adds a further image whose branches are resolved against the *same*
wrapper table.  On a cartridge with overlays the wrappers are linked once, into
`arm9.bin`, and an overlay that wanted one would branch to it across the module
boundary -- a call site the single-image form cannot see, because the overlay
links no wrapper of its own and therefore has nothing to count against.

ARM   `cond 1111 imm24`      -- the DS BIOS reads the number from bits 23..16.
THUMB `11011111 imm8`        -- the number is the whole operand byte.

Standard library only.
"""

import collections
import struct
import sys

# ARM7/ARM9 BIOS service numbers.  The decompression group is 0x10..0x18.
SWI_NAMES = {
    0x00: 'SoftReset', 0x01: 'RegisterRamReset(ARM9)/DelayLoop', 0x02: 'Halt',
    0x03: 'Stop/Sleep', 0x04: 'IntrWait', 0x05: 'VBlankIntrWait',
    0x06: 'Halt', 0x07: 'Sleep', 0x08: 'SoundBias', 0x09: 'Div',
    0x0A: 'WaitByLoop', 0x0B: 'CpuSet', 0x0C: 'CpuFastSet',
    0x0D: 'Sqrt', 0x0E: 'GetCRC16', 0x0F: 'IsDebugger',
    0x10: 'BitUnPack',
    0x11: 'LZ77UnCompReadNormalWrite8bit  (the GBA "LZ77UnComp")',
    0x12: 'LZ77UnCompReadByCallbackWrite16bit',
    0x13: 'HuffUnCompReadByCallback',
    0x14: 'RLUnCompReadNormalWrite8bit  (the GBA "RLUnComp")',
    0x15: 'RLUnCompReadByCallbackWrite16bit',
    0x16: 'Diff8bitUnFilterWrite8bit',
    0x17: 'Diff8bitUnFilterWrite16bit',
    0x18: 'Diff16bitUnFilter',
    0x1F: 'CustomHalt', 0x20: 'SoundDriverInit', 0x21: 'SoundDriverMode',
    0x22: 'SoundDriverMain', 0x23: 'SoundDriverVSync', 0x24: 'SoundChannelClear',
    0x25: 'MidiKey2Freq', 0x26: 'SoundWhatever0', 0x27: 'SoundWhatever1',
    0x28: 'SoundWhatever2', 0x29: 'SoundWhatever3', 0x2A: 'SoundDriverVSyncOff',
    0x2B: 'SoundDriverVSyncOn',
}
DECOMPRESSION = set(range(0x10, 0x19))


MAX_SWI = 0x2B          # the highest service the DS BIOS defines

def scan(data, base, strict=True):
    """Every SWI in the image.

    `strict` applies the two filters that separate a call from a coincidence:
    the ARM comment field must be `NN0000`, which is the form every SDK build
    emits, and the service number must be one the BIOS defines.  Without them
    a 1.5 MB image of mixed code and data reports thousands of `0xEF......`
    words that are not instructions at all.  Both totals are printed.
    """
    arm, thumb = [], []
    for i in range(0, len(data) - 3, 4):
        w = struct.unpack_from('<I', data, i)[0]
        if (w >> 28) == 0xF or (w >> 24) & 0xF != 0xF:
            continue
        n = (w >> 16) & 0xFF
        if strict and ((w & 0xFFFF) or n > MAX_SWI):
            continue
        nxt = struct.unpack_from('<I', data, i + 4)[0] if i + 8 <= len(data) else 0
        arm.append((base + i, n, nxt == 0xE12FFF1E))
    for i in range(0, len(data) - 1, 2):
        h = struct.unpack_from('<H', data, i)[0]
        if (h >> 8) != 0xDF:
            continue
        n = h & 0xFF
        if strict and n > MAX_SWI:
            continue
        nxt = struct.unpack_from('<H', data, i + 2)[0] if i + 4 <= len(data) else 0
        thumb.append((base + i, n, nxt == 0x4770))
    return arm, thumb


def branch_targets(data, base):
    """Resolve every ARM and THUMB branch in the image to its target.

    A linked SDK wrapper that nothing branches to is dead library code.  This
    is what separates "the decompression services are present in the binary"
    from "the game decompresses anything".
    """
    t = {}
    n = len(data)
    for i in range(0, n - 3, 4):
        w = struct.unpack_from('<I', data, i)[0]
        if (w >> 28) == 0xF:
            if (w & 0xFE000000) == 0xFA000000:            # blx immediate
                off = w & 0xFFFFFF
                off = off - 0x1000000 if off & 0x800000 else off
                t.setdefault(base + i + 8 + off * 4 + ((w >> 24) & 1) * 2,
                             []).append(('arm blx', base + i))
            continue
        if (w >> 25) & 7 == 5:                            # b / bl
            off = w & 0xFFFFFF
            off = off - 0x1000000 if off & 0x800000 else off
            t.setdefault(base + i + 8 + off * 4, []).append(
                ('arm bl' if (w >> 24) & 1 else 'arm b', base + i))
    for i in range(0, n - 3, 2):
        h = struct.unpack_from('<H', data, i)[0]
        if (h >> 11) != 0b11110:
            continue
        h2 = struct.unpack_from('<H', data, i + 2)[0]
        if (h2 >> 11) not in (0b11111, 0b11101):
            continue
        hi = h & 0x7FF
        hi = hi - 0x800 if hi & 0x400 else hi
        t.setdefault(base + i + 4 + (hi << 12) + (h2 & 0x7FF) * 2, []).append(
            ('thumb bl' if (h2 >> 11) == 0b11111 else 'thumb blx', base + i))
    return t


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    data = open(argv[1], 'rb').read()
    base = int(argv[argv.index('--base') + 1], 0) if '--base' in argv else 0
    loose_a, loose_t = scan(data, base, strict=False)
    arm, thumb = scan(data, base, strict=True)
    print('%s -- %d bytes' % (argv[1], len(data)))
    print('  %d words / %d halfwords match the SWI encoding at all'
          % (len(loose_a), len(loose_t)))
    print('  %d ARM + %d THUMB survive the two filters (comment field NN0000,'
          % (len(arm), len(thumb)))
    print('  service number <= 0x%02X)' % MAX_SWI)
    print()
    print('  of those, %d are followed by `bx lr` -- the shape of an SDK'
          % (sum(1 for _, _, w in arm + thumb if w)))
    print('  SVC wrapper, and the only form that is certainly an instruction.')
    print()
    c = collections.Counter()
    for _, n, w in arm:
        if w:
            c[('arm', n)] += 1
    for _, n, w in thumb:
        if w:
            c[('thumb', n)] += 1
    print('  %-6s %-5s %6s  %s' % ('SET', 'SWI', 'COUNT', 'SERVICE'))
    for (which, n), k in sorted(c.items(), key=lambda kv: -kv[1]):
        mark = '  <-- decompression' if n in DECOMPRESSION else ''
        print('  %-6s 0x%02X  %6d  %s%s'
              % (which, n, k, SWI_NAMES.get(n, '?'), mark))
    print()
    wrappers = [(a, n) for a, n, w in arm + thumb if w]
    sites = [(a, n) for a, n in wrappers if n in DECOMPRESSION]
    if sites:
        print('  decompression wrappers linked into this image:')
        for a, n in sorted(sites):
            print('    0x%08X  svc #0x%02X ; bx lr   %s'
                  % (a, n, SWI_NAMES.get(n, '?')))
    else:
        print('  no BIOS decompression wrapper is linked into this image.')
    print()
    print('  A wrapper being *linked* says only that the SDK library was')
    print('  linked.  The question is whether anything calls it, so every')
    print('  branch in the image is resolved and counted against each one.')
    tg = branch_targets(data, base)
    print('  %d distinct branch targets in this image' % len(tg))
    extra = []
    i = 0
    while i < len(argv):
        if argv[i] == '--also':
            spec = argv[i + 1]
            path, _, va = spec.partition('@')
            extra.append((path, int(va, 0) if va else 0))
            i += 1
        i += 1
    for path, va in extra:
        d2 = open(path, 'rb').read()
        t2 = branch_targets(d2, va)
        print('  %d distinct branch targets in %s (loaded at 0x%08X)'
              % (len(t2), path, va))
        for k, v in t2.items():
            tg.setdefault(k, []).extend((kind, src, path) for kind, src in v)
    if extra:
        print('  %d distinct branch targets over all %d images'
              % (len(tg), 1 + len(extra)))
    print()
    print('  %-12s %-6s %-46s %s' % ('WRAPPER', 'SWI', 'SERVICE', 'CALL SITES'))
    for a, n in sorted(wrappers):
        callers = tg.get(a, []) + tg.get(a | 1, [])
        mark = '  <-- decompression' if n in DECOMPRESSION else ''
        print('  0x%08X  0x%02X   %-46s %3d%s'
              % (a, n, SWI_NAMES.get(n, '?')[:46], len(callers), mark))
        for c in callers[:8]:
            kind, src = c[0], c[1]
            where = (' in ' + c[2]) if len(c) > 2 else ''
            print('        %-10s from 0x%08X%s' % (kind, src, where))


if __name__ == '__main__':
    main(sys.argv)
