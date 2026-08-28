# 07 — Media and the budget

How the 128 MiB was spent, classified from magic and arithmetic and never from
an extension. [`formats.py`](../tools/formats.py),
[`media_census.py`](../tools/media_census.py), [`sdat.py`](../tools/sdat.py),
[`deflate_control.py`](../tools/deflate_control.py).
[`reports/budget.txt`](../reports/budget.txt),
[`reports/media-census.txt`](../reports/media-census.txt),
[`reports/sdat.txt`](../reports/sdat.txt),
[`reports/file-census.csv`](../reports/file-census.csv).

---

## The cartridge

| | bytes | % of cartridge |
|---|---:|---:|
| header, tables, banner | 175,382 | 0.131% |
| ARM9 + ARM7 modules | 836,112 | 0.623% |
| **files** (the three overlays included) | **125,906,775** | **93.808%** |
| alignment slack between files | 2,999,807 | 2.235% |
| **unused tail, every byte `0xFF`** | **4,299,652** | **3.203%** |

**96.8% of the cartridge is in use.** *Tales of the Tempest* used 58.7% of its
own and left 41.3% — 52,806,648 zero bytes then exactly 2.5 MiB of `0xFF` — and
that emptiness is half of why nothing on it was compressed. Here there is one
filler byte, no boundary, and 4.3 MB spare on a 128 MiB part.

## The files, by class

| class | files | bytes | % cartridge | % file bytes |
|---|---:|---:|---:|---:|
| **audio** | 2,445 | 64,940,354 | **48.38%** | 51.58% |
| **container** (`EZBIND`) | 1,346 | 45,577,891 | **33.96%** | 36.20% |
| 3D animation (loose `.nsbca`) | 1,521 | 6,848,807 | 5.10% | 5.44% |
| **video** | 1 | 4,055,640 | 3.02% | 3.22% |
| other (in-house scripts, face data, overlays) | 860 | 2,665,907 | 1.99% | 2.12% |
| 2D graphics | 141 | 1,652,302 | 1.23% | 1.31% |
| font (`NFTR`) | 6 | 117,624 | 0.09% | 0.09% |
| geometry / collision | 54 | 27,524 | 0.02% | 0.02% |
| text | 1 | 20,726 | 0.02% | 0.02% |

A third of the cartridge is inside containers, and what is inside *them* is
overwhelmingly 3D: models 61.48% of member bytes, textures 15.11%, animation
14.71% ([03](03-file-system-and-containers.md)).

**Media is 51.40% of the cartridge** — audio plus video — and that is the number
to put beside the corpus:

| build | medium | media share | of what |
|---|---|---:|---|
| *Tales of Tactics*, i-appli 2004 | 369 KB | **63.3%** | of the package |
| *Tales of the Abyss*, PS2 2005 | 4.36 GB | **61.66%** | of the disc, 13.60 h of voice |
| **Tales of Innocence, DS 2007** | **128 MiB** | **51.40%** | **of the cartridge, 2.81 h of voice** |
| *Tales of Legendia*, PS2 2005 | 4.08 GB | **37.70%** | of the disc |
| *Tales of the Tempest*, DS 2006 | 64 MiB | **13.22%** | of the cartridge, 11 min 12 s of voice |

*Tales of Tactics* established a pattern — media dominates — and *Tales of the
Tempest* broke it so hard that the corpus recorded the break as a finding.
Innocence puts the pattern back. Whatever made Tempest's budget an outlier, it
was not the Nintendo DS: the same platform one year later spends half its
cartridge on media and fills the part.

---

## Audio

Two entirely separate stacks, and neither is the one Tempest used.

### CRI, for voice

[`media_census.py --cri`](../tools/media_census.py). Identified from the
`(c)CRI` marker each header carries, at the offset its own second field points
to — not from the file extension.

| kind | ch | rate | files | bytes | duration |
|---|---:|---:|---:|---:|---|
| **AHX** (MPEG-2 layer II) | 1 | 16,364 | **2,356** | 46,529,840 | **9,788.9 s = 2.72 h** |
| ADX (CRI ADPCM) | 1 | 16,364 | 87 | 3,050,844 | 330.8 s = 0.09 h |
| ADX | 2 | 32,728 | 1 | 6,627,478 | 180.0 s = 0.05 h |
| **total** | | | **2,444** | **56,208,162** | **10,299.8 s = 2.86 h** |

`/voice` alone is 2,443 files and **2.81 hours**. The single stereo ADX is
`/test/ed.adx` — three minutes exactly, the ending theme.

Duration is `samples / rate` from each header. For ADX that is exact. For AHX
the rate field is what the header declares and the encoder's own rate lives
inside the MPEG frames, so the AHX figure is quoted as the header's arithmetic
and not as a measured one; it is stated that way in the tool as well.

Beside the corpus: *Tales of the Abyss* has 13.60 hours of voice on a DVD;
*Tales of the Tempest* has **11 minutes 12 seconds** on a cartridge half this
size. Innocence has fifteen times Tempest's speech on twice the medium, and it
paid for it with a licensed MPEG codec.

### Nintendo, for music and effects

[`sdat.py`](../tools/sdat.py). One `SDAT`, 8,732,192 bytes, with a complete
`SYMB` block — every member is named.

| | members | bytes |
|---|---:|---:|
| `SWAR` wave archives | 68 | 4,976,384 |
| `STRM` streams | 310 | 3,436,256 |
| `SSEQ` sequences | 49 | 217,472 |
| `SSAR` sequence archives | 20 | 34,688 |
| `SBNK` banks | 69 | 29,472 |

The 310 streams are format 2, IMA-ADPCM, 396.8 seconds, all but one at 16,892 Hz
— and the rate is corroborated without trusting the field, because the DS sound
clock is 33,513,982 / 2 Hz and `rate × timer × 32` has to land on it:
16,892 × 31 × 32 = 16,756,864 and 47,605 × 11 × 32 = 16,756,960. The 819 `SWAV`
waves inside the archives are another 426.0 seconds.

**The music is sequenced.** 49 `SSEQ` against 69 banks and 68 wave archives is
the DS's own sound driver doing the work, exactly as on Tempest. The stream
names are legible — `STRM_ruca_Weak`, `STRM_ruca_Dead`, `STRM_ruca_Awakening` —
so the streams are battle voice clips held in the Nitro archive while the
narrative voice is CRI, two systems for one job.

---

## Video

One file. `/test/op.mods`, 4,055,640 bytes, 3.02% of the cartridge, and its
header reads:

| field | value |
|---|---|
| magic | `MODS` |
| `+0x04` | `N2\n\0` |
| frame count | **2,136** |
| frame size | **256 × 192** — both DS screens |
| audio sample rate | **32,000 Hz** |

and seven further header words whose meaning is not established here, printed
raw by the tool.

**No duration is quoted.** No frame-rate field is identified. 2,136 frames at
some plausible rate is somewhere between one and one and a half minutes, and a
number derived from a guess is worth less than no number — which is the same
decision *Tales of the Tempest* made about the `+0x04` count in its Actimagine
`VXDS` headers, and for the same reason.

---

## What is the largest thing on the cartridge

| bytes | file |
|---:|---|
| 8,732,192 | `/sound/ToI.sdat` |
| 6,627,478 | `/test/ed.adx` |
| 4,055,640 | `/test/op.mods` |
| 712,800 | overlay 0 |
| 591,079 | `/field/f161.bin` |
| 586,792 | `/field/f162.bin` |
| 586,752 | `/field/f048.bin` |
| 577,312 | overlay 1 |

Nothing here needed profiling before being written down. The corpus's rule —
*profile anything large that looks like filler, because it has paid three
times* — was applied anyway: the three largest are a Nitro sound archive, a
three-minute CRI stream and a Mobiclip video, all three parsed by their own
headers, and the field archives are `LZ77`-wrapped `EZBIND` whose members are
all classified.

---

## Duplication

[`crosstitle.py`](../tools/crosstitle.py),
[`reports/cross-title.txt`](../reports/cross-title.txt).

5,595 distinct contents in 6,375 files; 246 contents repeat, wasting 4,112,820
bytes — 3.3% of the file area, on a cartridge with 4.3 MB spare. The largest
repeats are `navimap_0.nbfc` … in **58 identical copies** of 15,360 bytes, ten
identical `btmap_027..034` model and texture pairs, and `f089.bin` / `f091.bin`
byte-identical at 152,720 bytes each — the two field archives that are also the
only two shipped uncompressed ([06](06-what-it-uses-instead.md)).

---

## Files nothing names

4,591 of the 6,378 file names are not spelled out anywhere in the image outside
the file name table, accounting for 87,415,064 bytes. **That is not a count of
dead files** and the tool says so in its own output: the loader builds most
names with format strings — `facechat/ev%04d.scr`, `chara%02d.nbfc`,
`facechat/sb%02d-%04d.scr` are all in the ARM9 — so a name that is never
spelled out is a name that is computed, not a file that is unused. The number
is reported because it is a real measurement of something; it is just not a
measurement of deadness. [99](99-open-questions.md).
