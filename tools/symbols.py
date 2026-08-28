#!/usr/bin/env python3
"""The C++ type names the executables kept, and what they name.

*Tales of the Tempest* (Nintendo DS, 2006) carried no symbol table, no
`.comment`, no company string and no source path: everything that repository
says about who built it comes from outside the image.  This cartridge is the
opposite case, and the reason is one build setting -- it was compiled with
run-time type information on, and RTTI has to keep the name of every
polymorphic class in the binary in order to work.

The names are stored the way the ARM C++ ABI writes a `type_info` name: the
length of the identifier in decimal, then the identifier, then a NUL.  So

    31cMappyComponentDSStandardEntity\\0

is the class `cMappyComponentDSStandardEntity`, 31 characters, and the decimal
prefix is what makes the scan exact instead of a guess -- a run of letters that
happens to follow a number is only accepted when the number is its length.

Names are grouped by their leading identifier so that a framework shows up as
a framework rather than as three hundred unrelated strings.

    python symbols.py FILE [FILE ...] [--all] [--prefix N]

Standard library only.
"""

import collections
import os
import re
import sys

PAT = re.compile(rb'(?<![0-9])(\d{1,3})([A-Za-z_][A-Za-z0-9_]{1,90})\x00')


def names(data):
    out = []
    for m in PAT.finditer(data):
        n = int(m.group(1))
        s = m.group(2)
        if len(s) == n:
            out.append((m.start(), s.decode()))
    return out


def group_of(s):
    """The framework or subsystem a class name belongs to.

    Strip the ABI's leading `c` or `i` -- this codebase spells concrete
    classes `cThing` and interfaces `iThing` -- and take the first
    capitalised word.
    """
    t = s
    if len(t) > 1 and t[0] in 'ci' and t[1].isupper():
        t = t[1:]
    m = re.match(r'[A-Z][a-z0-9]*', t)
    return m.group() if m else t[:8]


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    paths = [a for a in argv[1:] if not a.startswith('--')]
    show_all = '--all' in argv
    total = 0
    every = []
    for p in paths:
        d = open(p, 'rb').read()
        ns = names(d)
        total += len(ns)
        every.extend((os.path.basename(p), o, s) for o, s in ns)
        print('%-14s %8d bytes  %5d length-prefixed type names'
              % (os.path.basename(p), len(d), len(ns)))
    print()
    print('%d names over %d images' % (total, len(paths)))
    print()

    groups = collections.Counter()
    where = collections.defaultdict(set)
    for img, o, s in every:
        g = group_of(s)
        groups[g] += 1
        where[g].add(img)
    print('== by leading identifier ==')
    print('  %-16s %6s  %s' % ('GROUP', 'NAMES', 'IMAGES'))
    for g, n in groups.most_common():
        if n < 2 and not show_all:
            continue
        print('  %-16s %6d  %s' % (g, n, ', '.join(sorted(where[g]))))
    print()

    if show_all:
        print('== every name ==')
        for img, o, s in every:
            print('  %-14s 0x%06X  %s' % (img, o, s))


if __name__ == '__main__':
    main(sys.argv)
