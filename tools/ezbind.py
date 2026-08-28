#!/usr/bin/env python3
"""`EZBIND` -- the in-house container this cartridge indexes almost everything with.

*Tales of the Tempest* (Nintendo DS, 2006) had no container at all: 4,712 files
in one flat directory and a single Nintendo `SDAT`.  This cartridge has over a
thousand of them, and they are not a Nintendo format and not any of the *Tales*
envelopes section 6 of the codec specification lists.  The layout, read off the
bytes:

    +0x00  "EZBIND\\0\\0"
    +0x08  u32  member count
    +0x0C  u32  4 -- words per entry, and it is 4 on every archive here
    +0x10  entry[count], sixteen bytes each:
             +0x00  u32  offset of the member's name, from the file start
             +0x04  u32  size of the member in bytes
             +0x08  u32  offset of the member, from the file start
             +0x0C  u32  a 32-bit tag, distinct on every member of an archive
           name table -- NUL-terminated names, in entry order
           member data

The reading is checkable rather than assumed, and it is checked on every
archive: the name table has to begin exactly where the entry array ends, every
name offset has to land inside it, and the members have to tile the file from
the end of the name table to the last byte with no gap and no overlap.  An
archive that fails any of those is printed as failing.

The tag at +0x0C is not identified.  It is distinct within an archive and it is
not the member's size, offset or index; a name hash is the obvious guess and
nothing tried here reproduces it, so it is reported and not named.

Whole archives are sometimes wrapped in a BIOS `LZ77` stream -- 102 of the 104
field archives are -- and members are sometimes themselves `EZBIND`.  `--walk`
descends through both.

    python ezbind.py FILE                 header and members
    python ezbind.py FILE --check         the structural check only
    python ezbind.py DIR --census         every archive under a tree
    python ezbind.py DIR --walk           the same, descending into nesting
    python ezbind.py FILE --extract DIR   write the members out

Standard library only.
"""

import os
import struct
import sys

MAGIC = b'EZBIND\x00\x00'
BIOS_TYPES = (0x10, 0x11, 0x24, 0x28, 0x30, 0x81, 0x82)


class Bad(Exception):
    pass


def parse(d):
    if len(d) < 16 or d[:8] != MAGIC:
        raise Bad('not EZBIND')
    count, stride = struct.unpack_from('<II', d, 8)
    if stride != 4:
        raise Bad('entry stride %d words, not 4' % stride)
    if count <= 0 or 16 + count * 16 > len(d):
        raise Bad('member count %d does not fit in %d bytes' % (count, len(d)))
    return [struct.unpack_from('<IIII', d, 16 + i * 16) for i in range(count)]


def name_at(d, off):
    try:
        e = d.index(b'\x00', off)
    except ValueError:
        return '?'
    return d[off:e].decode('shift_jis', 'replace')


def check(d, members):
    """Every structural claim in the docstring, as a list of failures."""
    bad = []
    ent_end = 16 + len(members) * 16
    if members[0][0] != ent_end:
        bad.append('name table starts at 0x%X, entries end at 0x%X'
                   % (members[0][0], ent_end))
    data_start = min(m[2] for m in members)
    for n_off, size, off, tag in members:
        if not ent_end <= n_off < data_start:
            bad.append('name offset 0x%X outside the name table' % n_off)
            break
    for n_off, size, off, tag in members:
        if off + size > len(d):
            bad.append('member at 0x%X + %d runs past the end' % (off, size))
            break
    cur = data_start
    pad = 0
    for n_off, size, off, tag in sorted(members, key=lambda m: m[2]):
        if off != (cur + 3) & ~3:
            bad.append('member at 0x%X does not follow the previous one, '
                       'which ended at 0x%X' % (off, cur))
            break
        pad += off - cur
        cur = off + size
    if not (cur <= len(d) <= ((cur + 3) & ~3)):
        bad.append('members end at 0x%X, file is %d bytes' % (cur, len(d)))
    if len(set(m[3] for m in members)) != len(members):
        bad.append('the +0x0C tag repeats within this archive')
    return bad


def walk_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            out.append((os.path.relpath(full, root).replace(os.sep, '/'), full))
    out.sort()
    return out


def unwrap(d):
    """If d is a whole BIOS stream, decompress it.  Returns (data, how)."""
    if len(d) >= 4 and d[0] in BIOS_TYPES:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import ndscomp
            out, used = ndscomp.decompress(d, 0)
            if used == len(d) and len(out) > 16:
                return out, ndscomp.TYPES[d[0]]
        except Exception:
            pass
    return d, None


def census(root, deep):
    files = arcs = members = wrapped = nested = 0
    arc_bytes = mem_bytes = 0
    failed = []
    pending = []
    for name, path in walk_files(root):
        files += 1
        pending.append((name, open(path, 'rb').read()))
    while pending:
        name, d = pending.pop()
        d2, how = unwrap(d)
        if how and d2[:8] == MAGIC:
            wrapped += 1
            d = d2
        if d[:8] != MAGIC:
            continue
        try:
            ms = parse(d)
        except Bad:
            continue
        arcs += 1
        arc_bytes += len(d)
        members += len(ms)
        mem_bytes += sum(m[1] for m in ms)
        b = check(d, ms)
        if b:
            failed.append((name, b[0]))
        if deep:
            for n_off, size, off, tag in ms:
                sub, h2 = unwrap(d[off:off + size])
                if sub[:8] == MAGIC:
                    nested += 1
                    pending.append((name + '/' + name_at(d, n_off), sub))
    print('# %d files walked' % files)
    print('# %d EZBIND archives, %d bytes' % (arcs, arc_bytes))
    print('#   of which %d had to be decompressed first' % wrapped)
    if deep:
        print('#   of which %d are members of another archive' % nested)
    print('# %d members, %d bytes' % (members, mem_bytes))
    print('# %d archives failed the structural check' % len(failed))
    for n, b in failed[:40]:
        print('#   %s: %s' % (n, b))


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    target = argv[1]
    if '--census' in argv or '--walk' in argv:
        census(target, '--walk' in argv)
        return
    d = open(target, 'rb').read()
    d, how = unwrap(d)
    if how:
        print('# unwrapped a %s stream first' % how)
    if '--extract' in argv:
        out = argv[argv.index('--extract') + 1]
        ms = parse(d)
        os.makedirs(out, exist_ok=True)
        for n_off, size, off, tag in ms:
            base = os.path.basename(name_at(d, n_off)) or ('%08X' % tag)
            with open(os.path.join(out, base), 'wb') as f:
                f.write(d[off:off + size])
        print('%d members written to %s' % (len(ms), out))
        return
    members = parse(d)
    print('%s -- %d bytes, %d members' % (target, len(d), len(members)))
    bad = check(d, members)
    print('  structural check: %s' % ('OK' if not bad else 'FAILED'))
    for b in bad:
        print('    ! %s' % b)
    if '--check' not in argv:
        print('  %-30s %10s %10s  %s' % ('NAME', 'OFFSET', 'SIZE', 'TAG'))
        for n_off, size, off, tag in members:
            print('  %-30s 0x%08X %10d  0x%08X'
                  % (name_at(d, n_off)[:30], off, size, tag))


if __name__ == '__main__':
    main(sys.argv)
