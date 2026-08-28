#!/usr/bin/env python3
"""Does this build carry anything belonging to another title?

Two directions, because this is the first build in the corpus made by a studio
outside the *Tales* line:

  * **inwards** -- names, tags and assets belonging to earlier *Tales* games,
    which is what caught *Tales of the Abyss* carrying 109 of *Tales of
    Rebirth*'s sound effects;
  * **outwards** -- anything belonging to the developing studio's other work,
    which would say what the studio brought with it rather than what the
    series did.

A short needle is noise unless its chance rate is stated, so every count is
printed with the number of bytes it was drawn from and the expected number of
chance hits at that length.  Names are also matched against the cartridge's
**file name table**, where a hit is not a chance event at all.

    python crosstitle.py IMAGE FILESDIR

Standard library only.
"""

import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ndsrom import NDS
import ezbind

# Leads and signature nouns of the titles this corpus has documented.
TALES_NAMES = {
    'Phantasia 1995': ['cless', 'cress', 'mint', 'chester', 'arche', 'klarth',
                       'suzu', 'dhaos'],
    'Destiny 1997': ['stan', 'stahn', 'rutee', 'leon', 'philia', 'firia',
                     'mary', 'garr', 'woodrow', 'johnny', 'dimlos', 'dymlos',
                     'chaltier', 'atwight', 'igtenos', 'clemente',
                     'berselius', 'swordian'],
    'Eternia 2000': ['reid', 'rid', 'farah', 'keele', 'meredy', 'chat',
                     'ras', 'shizel'],
    'Destiny 2 2002': ['kyle', 'reala', 'loni', 'judas', 'nanaly', 'nanari',
                       'harold', 'elraine'],
    'Symphonia 2003': ['lloyd', 'colette', 'genis', 'raine', 'sheena',
                       'zelos', 'presea', 'regal', 'kratos'],
    'Rebirth 2004': ['veigue', 'mao', 'eugene', 'annie', 'tytree', 'hilda',
                     'claire', 'agarte'],
    'Legendia 2005': ['senel', 'shirley', 'will', 'chloe', 'norma', 'moses',
                      'jay', 'grune'],
    'Abyss 2005': ['luke', 'tear', 'jade', 'guy', 'natalia', 'anise', 'mieu'],
}

PROJECT_TAGS = [b'TO7', b'TO8', b'ToR', b'ToL', b'tox', b'tor_', b'no_se_',
                b'TOP', b'TOD', b'TOE', b'TOS', b'ToD2', b'TOT', b'ToT']

# Things the developing studio is known by, and the shapes a project tag takes.
STUDIO = [b'Dimps', b'DIMPS', b'dimps', b'DIMPS', b'Wolf', b'WOLF',
          b'Telenet', b'TELENET', b'Namco', b'NAMCO', b'namco',
          b'BANDAI', b'Bandai', b'bandai', b'Tales Studio', b'NT_DS',
          b'NTDS', b'Sonic', b'SONIC']


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    rom = open(argv[1], 'rb').read()
    r = NDS(rom)
    files, _ = r.fnt()
    root = argv[2]
    names = [p.rsplit('/', 1)[-1] for _, p in files]
    stems = set()
    for n in names:
        stems.add(n.rsplit('.', 1)[0].lower())

    n = len(rom)
    print('image %d bytes' % n)
    print('expected chance hits for a needle of length L: %.4f (L=4), '
          '%.1f (L=3)' % (n / 2.0 ** 32, n / 2.0 ** 24))
    print()

    print('== other titles\' names, as substrings of a file name ==')
    print('   (the name table is %d names; a hit here is not a chance event)'
          % len(names))
    any_hit = False
    for title, ns in TALES_NAMES.items():
        for name in ns:
            hits = sorted(x for x in names if name in x.rsplit('.', 1)[0].lower())
            if hits:
                any_hit = True
                print('  %-16s %-10s %3d files: %s'
                      % (title, name, len(hits),
                         ', '.join(hits[:8]) + (' ...' if len(hits) > 8 else '')))
    if not any_hit:
        print('  none')
    print()

    print('== other titles\' names, anywhere in the image ==')
    for title, ns in TALES_NAMES.items():
        for name in ns:
            for cand in (name.encode(), name.upper().encode(),
                         name.capitalize().encode()):
                c = rom.count(cand)
                if c:
                    print('  %-16s %-10s %6d hits (chance at this length: %.2f)'
                          % (title, cand.decode(), c, n / (256.0 ** len(cand))))
    print()

    print('== project tags ==')
    for t in PROJECT_TAGS:
        c = rom.count(t)
        print('  %-8s %6d hits, chance %.2f' % (t.decode('latin1'), c,
                                                n / (256.0 ** len(t))))
    print()

    print('== the developing studio, and studios generally ==')
    for t in STUDIO:
        c = rom.count(t)
        if c:
            print('  %-14s %6d hits, chance %.4f'
                  % (t.decode('latin1'), c, n / (256.0 ** len(t))))
    print()

    print('== the names *inside* the Nitro containers ==')
    print('   A model carries its own texture, material and palette names in a')
    print('   dictionary of sixteen-byte zero-padded strings.  Those are the')
    print('   names the artist typed, and they outlive a file being renamed.')
    # On *Tales of the Tempest* every model was a file of its own and reading
    # the top-level `.nsb*` files was the whole corpus.  Here almost every
    # model is a member of an `EZBIND` archive, and a hundred of those archives
    # are behind a BIOS `LZ77` stream, so the pass has to descend through both
    # or it reads a fifth of the models and reports the number as if it were
    # all of them.
    internal = collections.Counter()
    home = {}
    nitro = 0

    def harvest(d, label):
        for m in re.finditer(rb'[A-Za-z0-9_][A-Za-z0-9_.\-]{2,15}', d):
            t = m.group()
            if (len(t) < 16 and d[m.end():m.end() + 1] == b'\x00'
                    and m.start() % 4 == 0):
                nm = t.decode()
                internal[nm] += 1
                home.setdefault(nm, label)

    NITRO_MAGIC = (b'BMD0', b'BTX0', b'BCA0', b'BTA0', b'BMA0', b'BVA0', b'BTP0')
    for _, p in files:
        fp = os.path.join(root, p.lstrip('/').replace('/', os.sep))
        if not os.path.exists(fp):
            continue
        d = open(fp, 'rb').read()
        base = p.rsplit('/', 1)[-1]
        d, _how = ezbind.unwrap(d)
        if d[:4] in NITRO_MAGIC:
            nitro += 1
            harvest(d, base)
            continue
        if d[:8] != ezbind.MAGIC:
            continue
        try:
            ms = ezbind.parse(d)
        except Exception:
            continue
        for n_off, size, off, tag in ms:
            sub = d[off:off + size]
            if sub[:4] in NITRO_MAGIC:
                nitro += 1
                harvest(sub, '%s::%s' % (base, ezbind.name_at(d, n_off)))
    print('   %d distinct internal names across %d Nitro files'
          % (len(internal), nitro))
    for title, ns in TALES_NAMES.items():
        for name in ns:
            hits = sorted(k for k in internal if name in k.lower())
            if hits:
                print('   %-16s %-10s %s' % (title, name, ', '.join(
                    '%s (%dx, first in %s)' % (h, internal[h], home[h])
                    for h in hits[:6])))
    print()

    print('== date-shaped groups in internal names ==')
    datepat = re.compile(r'(0[4-9])(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])')
    for nm in sorted(internal):
        if datepat.search(nm):
            print('   %-24s in %s' % (nm, home[nm]))
    print()

    print('== byte-identical assets, which is how a shared asset shows ==')
    import hashlib
    h = collections.defaultdict(list)
    for _, p in files:
        fp = os.path.join(root, p.lstrip('/').replace('/', os.sep))
        if not os.path.exists(fp):
            continue
        d = open(fp, 'rb').read()
        h[hashlib.md5(d).hexdigest()].append((p.rsplit('/', 1)[-1], len(d)))
    groups = [v for v in h.values() if len(v) > 1]
    waste = sum((len(v) - 1) * v[0][1] for v in groups)
    print('  %d distinct contents in %d files; %d contents repeat, '
          '%d duplicate bytes' % (len(h), len(names), len(groups), waste))
    print('  the largest repeats:')
    for v in sorted(groups, key=lambda v: -(len(v) - 1) * v[0][1])[:15]:
        print('    %2d copies of %8d bytes: %s'
              % (len(v), v[0][1], ', '.join(x[0] for x in v[:8])))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
