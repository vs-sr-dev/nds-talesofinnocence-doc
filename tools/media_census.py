#!/usr/bin/env python3
"""How much audio and video is on the cartridge, measured from the headers.

Bytes are easy; hours are the number the rest of the corpus quotes, and they
come from the streams' own declared sample counts rather than from a guess at
a bitrate.

  * `STRM` -- the Nitro streamed-audio file.  Its `HEAD` block carries the
    sample format, the sample rate and the sample count, so the duration is
    arithmetic.
  * `SWAV` inside `SWAR` -- the same three fields, per wave.
  * `VXDS` -- Actimagine's video container.  Its header is read and every
    field printed; the ones this file is prepared to name are the frame size,
    the 16.16 frame rate, the audio sample rate and the channel count.  The
    count at +4 is left unnamed because nothing here establishes its unit,
    and a duration derived from a guess is worth less than no duration.

    python media_census.py SDATFILE VXFILE [VXFILE...]
    python media_census.py --cri DIR         every CRI ADX / AHX stream
    python media_census.py --mods FILE       Actimagine Mobiclip header

Two formats were added for *Tales of Innocence*, which ships no `VXDS` and no
`SWAV` voice at all.  Its speech is 2,444 CRI streams, whose header states the
sample rate and the sample count, so a duration is a division rather than a
guess.  Its video is a single Actimagine **Mobiclip** file, `MODS`, and there
the frame count and the frame size are readable and the frame *rate* is not --
so, as with `VXDS` on the previous cartridge, no duration is quoted for it.

Standard library only.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdat import Sdat

WAVE_FMT = {0: 'PCM8', 1: 'PCM16', 2: 'IMA-ADPCM'}


def strm_info(buf):
    if buf[:4] != b'STRM':
        return None
    # A STRM's header is sixteen bytes and its blocks follow immediately;
    # there is no offset table, unlike SDAT itself.
    o = 0x10
    if buf[o:o + 4] != b'HEAD':
        o = struct.unpack_from('<I', buf, 0x10)[0]
    if buf[o:o + 4] != b'HEAD':
        return None
    fmt = buf[o + 0x08]
    loop = buf[o + 0x09]
    chans = struct.unpack_from('<H', buf, o + 0x0A)[0]
    rate = struct.unpack_from('<H', buf, o + 0x0C)[0]
    timer = struct.unpack_from('<H', buf, o + 0x0E)[0]
    nsamp = struct.unpack_from('<I', buf, o + 0x14)[0]
    nblk = struct.unpack_from('<I', buf, o + 0x1C)[0]
    return dict(format=fmt, loop=loop, rate=rate, timer=timer, samples=nsamp,
                blocks=nblk, channels=chans, size=len(buf))


def swar_waves(buf):
    if buf[:4] != b'SWAR':
        return []
    n = struct.unpack_from('<I', buf, 0x38)[0]
    out = []
    for i in range(n):
        o = struct.unpack_from('<I', buf, 0x3C + i * 4)[0]
        if o + 12 > len(buf):
            continue
        fmt = buf[o]
        loop = buf[o + 1]
        rate = struct.unpack_from('<H', buf, o + 2)[0]
        nonloop = struct.unpack_from('<H', buf, o + 6)[0]
        looplen = struct.unpack_from('<I', buf, o + 8)[0]
        total_words = nonloop + looplen
        out.append((fmt, rate, total_words * 4))
    return out


def vx_header(buf):
    f = struct.unpack_from('<12I', buf, 0)
    return dict(magic=buf[:4], count=f[1], width=f[2], height=f[3],
                fps_fixed=f[4], f20=f[5], rate=f[6], channels=f[7],
                f32=f[8], f36=f[9], f40=f[10], f44=f[11])


def cri_header(b):
    """CRI ADX / AHX.  Returns None if this is not one.

    +0x00 u16 be 0x8000, +0x02 u16 be the offset at which the stream starts,
    and the six bytes ending two before it read `(c)CRI`.  +0x04 is the format
    code -- 3 is ADX ADPCM, 0x10 and 0x11 are AHX -- +0x05 the channel count,
    +0x08 a big-endian sample rate and +0x0C a big-endian sample count.
    """
    if len(b) < 20 or b[0] != 0x80 or b[1] != 0x00:
        return None
    off = struct.unpack_from('>H', b, 2)[0]
    if off + 4 > len(b) or b[off - 2:off + 4] != b'(c)CRI':
        return None
    fmt, ch = b[4], b[7]
    rate, samples = struct.unpack_from('>II', b, 8)
    return dict(kind={3: 'ADX', 0x10: 'AHX', 0x11: 'AHX'}.get(fmt,
                                                              'code %d' % fmt),
                fmt=fmt, ch=ch, rate=rate, samples=samples,
                secs=samples / float(rate) if rate else 0.0)


def mods_header(b):
    """Actimagine Mobiclip, `MODS`.  Every header word, named where it is
    established and printed raw where it is not."""
    f = struct.unpack_from('<13I', b, 0)
    return dict(magic=b[:4], tag=b[4:8], frames=f[2], width=f[3], height=f[4],
                w14=f[5], w18=f[6], rate=f[7], w20=f[8], w24=f[9], w28=f[10],
                w2c=f[11], w30=f[12])


def cri_census(root):
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            with open(p, 'rb') as fh:
                head = fh.read(64)
            h = cri_header(head)
            if h:
                h['path'] = os.path.relpath(p, root).replace(os.sep, '/')
                h['size'] = os.path.getsize(p)
                rows.append(h)
    print('== CRI ADX / AHX streams ==')
    print('  %d streams, %d bytes' % (len(rows), sum(r['size'] for r in rows)))
    by = {}
    for r in rows:
        k = (r['kind'], r['ch'], r['rate'])
        a, n, sec = by.get(k, (0, 0, 0.0))
        by[k] = (a + 1, n + r['size'], sec + r['secs'])
    print('  %-6s %3s %8s %7s %13s %14s'
          % ('KIND', 'CH', 'RATE', 'FILES', 'BYTES', 'DURATION'))
    tot = 0.0
    for (kind, ch, rate), (a, n, sec) in sorted(by.items()):
        tot += sec
        print('  %-6s %3d %8d %7d %13d %10.1f s = %.2f h'
              % (kind, ch, rate, a, n, sec, sec / 3600.0))
    print('  %-6s %3s %8s %7d %13d %10.1f s = %.2f h'
          % ('TOTAL', '', '', len(rows), sum(r['size'] for r in rows),
             tot, tot / 3600.0))
    print()
    by_dir = {}
    for r in rows:
        d = r['path'].split('/')[0]
        a, n, sec = by_dir.get(d, (0, 0, 0.0))
        by_dir[d] = (a + 1, n + r['size'], sec + r['secs'])
    print('  by directory')
    for d, (a, n, sec) in sorted(by_dir.items(), key=lambda kv: -kv[1][1]):
        print('    %-12s %6d files %12d bytes %10.1f s = %.2f h'
              % (d, a, n, sec, sec / 3600.0))
    print()
    print('  the five longest')
    for r in sorted(rows, key=lambda r: -r['secs'])[:5]:
        print('    %-44s %8.2f s  %s %d Hz'
              % (r['path'], r['secs'], r['kind'], r['rate']))


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    if argv[1] == '--cri':
        cri_census(argv[2])
        return 0
    if argv[1] == '--mods':
        b = open(argv[2], 'rb').read()
        h = mods_header(b)
        print('== Actimagine Mobiclip ==')
        print('  %s -- %d bytes' % (os.path.basename(argv[2]), len(b)))
        print('  magic            %r' % h['magic'])
        print('  +0x04            %r' % h['tag'])
        print('  frame count      %d' % h['frames'])
        print('  frame size       %d x %d' % (h['width'], h['height']))
        print('  audio rate       %d Hz' % h['rate'])
        print('  the remaining header words, unnamed because nothing here')
        print('  establishes their meaning:')
        for k in ('w14', 'w18', 'w20', 'w24', 'w28', 'w2c', 'w30'):
            print('    +0x%s = %d (0x%08X)' % (k[1:], h[k], h[k]))
        print('  No frame rate field is identified, so no duration is quoted.')
        return 0
    sd = Sdat(open(argv[1], 'rb').read())
    syms = sd.symbols()
    fat = sd.fat()
    names = {}
    info = sd.info()

    print('== the sound archive ==')
    kinds = {}
    for o, sz in fat:
        kinds.setdefault(sd.d[o:o + 4], []).append(sz)
    for k, v in sorted(kinds.items(), key=lambda kv: -sum(kv[1])):
        print('  %-6s %5d members, %10d bytes'
              % (k.decode('latin1'), len(v), sum(v)))
    print()

    print('== streamed audio (STRM), from each stream\'s own HEAD block ==')
    groups = {}
    strm_names = syms.get('STRM', [])
    total_sec = 0.0
    rows = []
    for i, (o, sz) in enumerate(fat):
        if sd.d[o:o + 4] != b'STRM':
            continue
        h = strm_info(sd.d[o:o + sz])
        if not h or not h['rate']:
            continue
        sec = h['samples'] / float(h['rate'])
        total_sec += sec
        rows.append((i, sz, h, sec))
    # name them by matching the FAT index against the STRM record's file id
    print('  %d streams, %d bytes, %.1f seconds = %.2f hours'
          % (len(rows), sum(sz for _, sz, _, _ in rows), total_sec,
             total_sec / 3600.0))
    fmts = {}
    rates = {}
    for _, _, h, sec in rows:
        fmts[h['format']] = fmts.get(h['format'], 0) + 1
        rates[h['rate']] = rates.get(h['rate'], 0) + 1
    for f, n in sorted(fmts.items()):
        print('    format %d (%s): %d streams' % (f, WAVE_FMT.get(f, '?'), n))
    for r, n in sorted(rates.items()):
        print('    %d Hz: %d streams' % (r, n))
    ch = {}
    for _, _, h, _ in rows:
        ch[h['channels']] = ch.get(h['channels'], 0) + 1
    print('    channel counts: %s' % dict(sorted(ch.items())))
    print('    the rate field is corroborated by the timer beside it:')
    print('    the DS sound clock is 33,513,982 / 2 Hz, and rate x timer x 32')
    print('    should land on it.')
    seen = set()
    for _, _, h, _ in rows:
        k = (h['rate'], h['timer'])
        if k in seen or not h['timer']:
            continue
        seen.add(k)
        print('      %6d Hz, timer %3d -> %d x %d x 32 = %d'
              % (h['rate'], h['timer'], h['rate'], h['timer'],
                 h['rate'] * h['timer'] * 32))
    print()

    # split by symbol prefix, which is how the game groups them
    print('== streams by name prefix ==')
    pref = {}
    for idx, name in enumerate(strm_names):
        if not name:
            continue
        p = name.split('_')[0]
        pref.setdefault(p, []).append(name)
    for p, v in sorted(pref.items(), key=lambda kv: -len(kv[1])):
        print('  %-10s %5d  e.g. %s' % (p, len(v), ', '.join(v[:3])))
    print()

    print('== sampled waves (SWAV inside SWAR) ==')
    nw = 0
    wb = 0
    wsec = 0.0
    for o, sz in fat:
        if sd.d[o:o + 4] != b'SWAR':
            continue
        for fmt, rate, nbytes in swar_waves(sd.d[o:o + sz]):
            nw += 1
            wb += nbytes
            if rate:
                spb = {0: 1, 1: 2, 2: 0.5}.get(fmt, 1)
                wsec += (nbytes / spb) / float(rate)
    print('  %d waves, %d bytes, %.1f seconds = %.2f hours'
          % (nw, wb, wsec, wsec / 3600.0))
    print()

    print('== video (Actimagine VXDS) ==')
    print('  %-24s %9s %6s %5s %5s %9s %5s %10s'
          % ('FILE', 'BYTES', '+4', 'W', 'H', 'FPS(16.16)', 'CH', 'RATE'))
    vb = 0
    for p in argv[2:]:
        b = open(p, 'rb').read()
        h = vx_header(b)
        vb += len(b)
        print('  %-24s %9d %6d %5d %5d %9.4f %5d %10d'
              % (os.path.basename(p), len(b), h['count'], h['width'],
                 h['height'], h['fps_fixed'] / 65536.0, h['channels'],
                 h['rate']))
    print('  %d files, %d bytes' % (len(argv) - 2, vb))
    print('  the remaining header words are printed raw because their meaning')
    print('  is not established here:')
    for p in argv[2:]:
        h = vx_header(open(p, 'rb').read())
        print('    %-24s +20=%d +32=%d +36=%d +40=%d +44=%d'
              % (os.path.basename(p), h['f20'], h['f32'], h['f36'],
                 h['f40'], h['f44']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
