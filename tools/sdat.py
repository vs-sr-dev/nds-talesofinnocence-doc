#!/usr/bin/env python3
"""Read a Nitro `SDAT` sound archive: symbols, records, and every member.

`SDAT` is the NitroSDK's own sound container.  It carries up to eight record
tables -- sequences, sequence archives, banks, wave archives, players, groups,
stream players and streams -- a `FAT` of file extents, and, when the build was
made with symbols on, a `SYMB` block holding **the name of every entry**.

That last block is why this file exists.  A `Tales` disc's sound-effect names
are what caught *Tales of the Abyss* carrying 109 of *Tales of Rebirth*'s, so
the equivalent question on a cartridge is answerable only if the names are
still there.

    python sdat.py FILE                 blocks, counts, and whether SYMB is on
    python sdat.py FILE --names         every symbol, by table
    python sdat.py FILE --members       one line per FAT member
    python sdat.py FILE --extract DIR   write every member out

Standard library only.
"""

import os
import struct
import sys

TABLES = ['SEQ', 'SEQARC', 'BANK', 'WAVEARC', 'PLAYER', 'GROUP',
          'PLAYER2', 'STRM']


class Sdat(object):
    def __init__(self, data):
        if data[:4] != b'SDAT':
            raise ValueError('not an SDAT')
        self.d = data
        self.magic = data[:4]
        self.bom = struct.unpack_from('<H', data, 4)[0]
        self.version = struct.unpack_from('<H', data, 6)[0]
        self.size = struct.unpack_from('<I', data, 8)[0]
        self.hdr_size = struct.unpack_from('<H', data, 12)[0]
        self.nblocks = struct.unpack_from('<H', data, 14)[0]
        self.blocks = []
        for i in range(self.nblocks):
            off, sz = struct.unpack_from('<II', data, 0x10 + i * 8)
            tag = data[off:off + 4] if off else b''
            self.blocks.append((tag, off, sz))

    def block(self, tag):
        for t, o, s in self.blocks:
            if t == tag:
                return o, s
        return None, None

    def symbols(self):
        """Return {table: [name or None, ...]} from the SYMB block."""
        o, _ = self.block(b'SYMB')
        if o is None:
            return {}
        out = {}
        for i, name in enumerate(TABLES):
            rec = struct.unpack_from('<I', self.d, o + 8 + i * 4)[0]
            if not rec:
                out[name] = []
                continue
            p = o + rec
            n = struct.unpack_from('<I', self.d, p)[0]
            names = []
            # A SEQARC entry is a pair -- its own name, then the offset of the
            # sub-table naming the sequences inside it -- so its stride is 8.
            stride = 8 if name == 'SEQARC' else 4
            for k in range(n):
                so = struct.unpack_from('<I', self.d, p + 4 + k * stride)[0]
                if so == 0:
                    names.append(None)
                    continue
                q = o + so
                e = self.d.index(b'\x00', q)
                names.append(self.d[q:e].decode('shift_jis', 'replace'))
            out[name] = names
        return out

    def fat(self):
        o, _ = self.block(b'FAT ')
        if o is None:
            return []
        n = struct.unpack_from('<I', self.d, o + 8)[0]
        out = []
        for i in range(n):
            p = o + 12 + i * 16
            s, sz = struct.unpack_from('<II', self.d, p)
            out.append((s, sz))
        return out

    def info(self):
        """Return {table: [record tuples]} from the INFO block."""
        o, _ = self.block(b'INFO')
        if o is None:
            return {}
        out = {}
        for i, name in enumerate(TABLES):
            rec = struct.unpack_from('<I', self.d, o + 8 + i * 4)[0]
            if not rec:
                out[name] = []
                continue
            p = o + rec
            n = struct.unpack_from('<I', self.d, p)[0]
            offs = [struct.unpack_from('<I', self.d, p + 4 + k * 4)[0]
                    for k in range(n)]
            out[name] = [(o + x) if x else None for x in offs]
        return out


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    s = Sdat(open(argv[1], 'rb').read())
    args = argv[2:]
    syms = s.symbols()
    fat = s.fat()
    if '--names' in args:
        for t in TABLES:
            names = syms.get(t, [])
            print('== %s: %d entries ==' % (t, len(names)))
            for i, n in enumerate(names):
                print('  %4d  %s' % (i, n if n else '<no symbol>'))
        return 0
    if '--members' in args:
        print('# index\tstart\tsize\tmagic')
        for i, (o, sz) in enumerate(fat):
            print('%d\t%d\t%d\t%r' % (i, o, sz, s.d[o:o + 4]))
        return 0
    if '--extract' in args:
        out = args[args.index('--extract') + 1]
        os.makedirs(out, exist_ok=True)
        for i, (o, sz) in enumerate(fat):
            open(os.path.join(out, 'file%04d.bin' % i), 'wb').write(s.d[o:o + sz])
        print('%d members' % len(fat))
        return 0

    print('%s -- %d bytes' % (os.path.basename(argv[1]), len(s.d)))
    print('  magic %r, BOM 0x%04X, version 0x%04X' % (s.magic, s.bom, s.version))
    print('  declared size %d, header %d bytes, %d blocks'
          % (s.size, s.hdr_size, s.nblocks))
    for t, o, sz in s.blocks:
        print('    %-6s at 0x%08X, %d bytes' % (t.decode('latin1'), o, sz))
    print('  SYMB present: %s' % ('yes' if syms else 'no'))
    total = 0
    for t in TABLES:
        n = len(syms.get(t, []))
        named = sum(1 for x in syms.get(t, []) if x)
        if n:
            print('    %-8s %5d entries, %5d named' % (t, n, named))
            total += n
    print('  FAT members: %d' % len(fat))
    kinds = {}
    for o, sz in fat:
        kinds[s.d[o:o + 4]] = kinds.get(s.d[o:o + 4], 0) + 1
    for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print('    %-8r %5d' % (k, v))
    print('  member bytes: %d' % sum(sz for _, sz in fat))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
