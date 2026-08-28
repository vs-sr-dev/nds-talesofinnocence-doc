#!/usr/bin/env python3
"""Strings, build stamps, source paths and anything else left in the image.

Reads ASCII and Shift-JIS runs out of whichever files it is given and sorts
them into the categories the corpus keeps asking about: build stamps, SDK and
middleware names, absolute source paths, debug and diagnostic text, file names
the code carries, and English text in a Japan-only release.

    python leftovers.py FILE [FILE...] [--min 6] [--all] [--jis]
    python leftovers.py --tree DIR --rom IMAGE

`--tree` is the other half of the same question and it was inline on the
previous cartridge: which *files* say `test`, `dbg`, `dummy`, `sample` or
`copy` in their names, how many bytes that is, whether the same is true of the
members inside the containers, and -- because a name is not evidence of being
dead -- whether anything outside the file name table mentions each one.  A
file nothing refers to may still be loaded by a name the code builds with
`%s`, so the count is reported as *unmentioned*, not as unused.

Standard library only.
"""

import os
import re
import struct
import sys

ASCII = re.compile(rb'[\x20-\x7E\t]{4,}')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

DATE = re.compile(r'^(%s) [ 0-3][0-9] (19|20)[0-9]{2}$' % '|'.join(MONTHS))
TIME = re.compile(r'^[0-2][0-9]:[0-5][0-9]:[0-5][0-9]$')
PATH = re.compile(r'([A-Za-z]:[\\/][^\s"\']{3,}|/[a-z][A-Za-z0-9_./-]{6,}'
                  r'|[A-Za-z0-9_]+\.(?:c|cpp|h|hpp|s|asm|nef|elf|arm9|arm7|bin))')
SDK = re.compile(r'(NITRO|Nitro|nitro|SDK|Actimagine|MobiClip|Mobiclip|CRI|'
                 r'RenderWare|Metrowerks|CodeWarrior|gcc|GCC|libc|Nintendo|'
                 r'NINTENDO|Dimps|DIMPS|dimps|Namco|NAMCO|BANDAI|Bandai|'
                 r'Wolf ?Team|Telenet|VX|Copyright|copyright|\(C\)|\(c\))')
DEBUG = re.compile(r'(debug|DEBUG|Debug|assert|ASSERT|error|ERROR|Error|'
                   r'warning|WARNING|TEST|test mode|FATAL|panic|dump|DUMP|'
                   r'%[0-9#.\-]*[dsxXfcp])')
FILENAME = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.\- ]{1,40}\.'
                      r'(?:nsbmd|nsbca|nsbta|nsbma|nsbva|nbm|mes|vx|sdat|bin|'
                      r'ANA|APA|ASC|vtx|srf|dat|imd|bmp|bnr|char|plt|nsb[a-z]+)$')


def runs(data, minlen):
    for m in ASCII.finditer(data):
        s = m.group()
        if len(s) >= minlen:
            yield m.start(), s.decode('ascii')


def jis_runs(data, minlen=4):
    """Shift-JIS double-byte runs -- lead 0x81..0x9F / 0xE0..0xEF."""
    out = []
    i = 0
    n = len(data)
    while i < n - 1:
        b = data[i]
        if (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF):
            j = i
            while j < n - 1:
                c = data[j]
                if not (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF):
                    break
                d = data[j + 1]
                if not (0x40 <= d <= 0x7E or 0x80 <= d <= 0xFC):
                    break
                j += 2
            if (j - i) // 2 >= minlen:
                try:
                    out.append((i, data[i:j].decode('shift_jis')))
                except UnicodeDecodeError:
                    pass
            i = max(j, i + 2)
        else:
            i += 1
    return out


DEBUG_NAME = re.compile(
    r'(?:^|[/_])(test|tst|dbg|debug|dummy|sample|temp|tmp|old|bak|work|copy)'
    r'(?:[0-9_./]|$)', re.I)


def tree_census(root, rom_path):
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ezbind
    rom = open(rom_path, 'rb').read()

    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            files.append((os.path.relpath(full, root).replace(os.sep, '/'),
                          full))
    files.sort()

    hits = [(rel, os.path.getsize(p)) for rel, p in files
            if DEBUG_NAME.search(rel) or rel.rsplit('/', 1)[-1].startswith('_')]
    tot_files = sum(os.path.getsize(p) for _, p in files)
    print('== files whose name says test, debug, dummy, sample or copy ==')
    print('  %d of %d files, %d of %d bytes (%.2f%%)'
          % (len(hits), len(files), sum(n for _, n in hits), tot_files,
             100.0 * sum(n for _, n in hits) / tot_files if tot_files else 0))
    for rel, n in sorted(hits, key=lambda h: -h[1])[:30]:
        print('  %10d  %s' % (n, rel))
    print()

    mn = mb = 0
    examples = []
    for rel, p in files:
        d, how = ezbind.unwrap(open(p, 'rb').read())
        if d[:8] != ezbind.MAGIC:
            continue
        try:
            ms = ezbind.parse(d)
        except Exception:
            continue
        for n_off, size, off, tag in ms:
            nm = ezbind.name_at(d, n_off)
            if DEBUG_NAME.search(nm) or nm.startswith('_'):
                mn += 1
                mb += size
                if len(examples) < 12:
                    examples.append((rel, nm, size))
    print('== members inside the containers, same test ==')
    print('  %d members, %d bytes' % (mn, mb))
    for a, b, c in examples:
        print('  %10d  %s :: %s' % (c, a, b))
    print()

    print('== which file names are mentioned anywhere outside the name table ==')
    print('   The file name table itself is excluded, so a mention means some')
    print('   payload or executable spells the name out.  A name that is never')
    print('   spelled out may still be built at run time with a format string,')
    print('   so this counts *unmentioned*, not *unused*.')
    fnt_off, fnt_size = struct.unpack_from('<II', rom, 0x40)
    body = rom[:fnt_off] + rom[fnt_off + fnt_size:]
    # One pass over the image collecting every printable run, rather than one
    # pass per file name: 6,378 searches of 134 MB is an hour, and this is a
    # second.
    # Reduce the image to its printable runs once, rather than searching the
    # whole 134 MB per name: 6,378 searches of the full image takes an hour,
    # and 6,378 searches of the few megabytes of text in it takes seconds.
    text = bytes(1).join(m.group() for m in
                        re.finditer(rb'[ -~]{4,200}', body))
    unmentioned = []
    for rel, p in files:
        base = rel.rsplit('/', 1)[-1].encode('shift_jis', 'replace')
        if base not in text:
            unmentioned.append((rel, os.path.getsize(p)))
    print('  the image reduces to %d bytes of printable text outside the '
          'name table' % len(text))
    print('  %d of %d file names are not spelled out anywhere else, %d bytes'
          % (len(unmentioned), len(files),
             sum(n for _, n in unmentioned)))
    for rel, n in sorted(unmentioned, key=lambda h: -h[1])[:25]:
        print('  %10d  %s' % (n, rel))


def main(argv):
    if '--tree' in argv:
        tree_census(argv[argv.index('--tree') + 1],
                    argv[argv.index('--rom') + 1])
        return
    files = [a for a in argv[1:] if not a.startswith('--')]
    if not files:
        raise SystemExit(__doc__)
    minlen = int(argv[argv.index('--min') + 1]) if '--min' in argv else 6
    for path in files:
        data = open(path, 'rb').read()
        allruns = list(runs(data, minlen))
        print('=' * 72)
        print('%s -- %d bytes, %d printable runs of %d or more'
              % (os.path.basename(path), len(data), len(allruns), minlen))
        print('=' * 72)

        stamps = [(o, s) for o, s in allruns if DATE.match(s.strip())]
        times = [(o, s) for o, s in allruns if TIME.match(s.strip())]
        print('\n-- build stamps (__DATE__ / __TIME__ shape) --')
        for o, s in stamps:
            near = [t for to, t in times if 0 < to - o <= 32]
            print('  0x%08X  %s%s' % (o, s, '   ' + near[0] if near else ''))
        if not stamps:
            print('  none')

        print('\n-- SDK, middleware and company names --')
        seen = set()
        for o, s in allruns:
            if SDK.search(s) and s not in seen:
                seen.add(s)
                print('  0x%08X  %s' % (o, s))

        print('\n-- absolute paths and source file names --')
        seen = set()
        for o, s in allruns:
            for m in PATH.finditer(s):
                t = m.group()
                if t not in seen:
                    seen.add(t)
                    print('  0x%08X  %s' % (o, t))

        print('\n-- file names the code carries --')
        seen = set()
        for o, s in allruns:
            if FILENAME.match(s.strip()) and s not in seen:
                seen.add(s)
                print('  0x%08X  %s' % (o, s.strip()))

        print('\n-- diagnostics, format strings and debug text --')
        seen = set()
        for o, s in allruns:
            if DEBUG.search(s) and s not in seen:
                seen.add(s)
                print('  0x%08X  %s' % (o, s))

        # An asset that shipped in its authoring-tool form carries provenance
        # the compiled form does not: who exported it, from which machine,
        # when, and from what file.  Those attributes hold Shift-JIS, so they
        # cannot be recovered from ASCII runs alone.
        try:
            text = data.decode('shift_jis', 'replace')
        except Exception:
            text = ''
        prov = re.findall(r'<(?:original_)?(?:create|generator)[^>]*>', text)
        paths = re.findall(r'(?:path|source|file)="([^"]+)"', text)
        if prov or paths:
            print('\n-- authoring-tool provenance --')
            for t in dict.fromkeys(prov):
                print('  %s' % t.strip())
            for t in dict.fromkeys(paths):
                print('  path: %s' % t)

        if '--jis' in argv:
            print('\n-- Shift-JIS runs --')
            for o, s in jis_runs(data)[:400]:
                print('  0x%08X  %s' % (o, s))

        if '--all' in argv:
            print('\n-- every run --')
            for o, s in allruns:
                print('  0x%08X  %s' % (o, s))
        print()


if __name__ == '__main__':
    main(sys.argv)
