# 03 — The file system and the container

[`ndsrom.py`](../tools/ndsrom.py), [`ezbind.py`](../tools/ezbind.py).
[`reports/nds-files.txt`](../reports/nds-files.txt),
[`reports/ezbind-census.txt`](../reports/ezbind-census.txt),
[`reports/file-census.csv`](../reports/file-census.csv).

---

## The Nitro file system

| | |
|---|---|
| FAT entries | **6,378** |
| named files | 6,375 |
| directories | **156** |
| FAT entries with no name | **3** |
| highest FAT end | 129,918,076 = the header's declared `ntr_rom_size`, exactly |

The three unnamed entries are the three ARM9 overlays, which is where overlays
live on this platform — the overlay table gives a file id and the FAT gives the
bytes. *Tales of the Tempest* had **zero** unnamed entries because it had no
overlays at all; this is the first cartridge in this corpus where the overlay
path is exercised ([04](04-executables.md)).

The names are real names, in real directories, and they describe what they hold.

| directory | files | bytes | % of file bytes |
|---|---:|---:|---:|
| `/voice` | 2,443 | 49,580,684 | 38.95% |
| `/field` | 158 | 17,216,369 | 13.53% |
| `/battle` | 524 | 16,864,205 | 13.25% |
| `/test` | 2 | 10,683,118 | 8.39% |
| `/sound` | 1 | 8,732,192 | 6.86% |
| `/motion` | 1,521 | 6,848,807 | 5.38% |
| `/chara` | 217 | 4,804,676 | 3.77% |
| `/world` | 200 | 2,889,756 | 2.27% |
| `/navi` | 100 | 1,536,000 | 1.21% |
| `/facedata` | 111 | 1,398,988 | 1.10% |
| `/_unnamed` (the overlays) | 3 | 1,379,968 | 1.08% |
| `/facechat` | 786 | 1,368,054 | 1.07% |
| `/weapon` | 252 | 1,081,184 | 0.85% |
| `/cutin` | 9 | 1,052,976 | 0.83% |
| `/staff` | 15 | 798,676 | 0.63% |
| `/title` | 17 | 484,540 | 0.38% |
| `/menu` | 9 | 368,140 | 0.29% |
| `/font` | 6 | 117,624 | 0.09% |
| `/subdisp` | 3 | 60,060 | 0.05% |
| `/quest` | 1 | 20,726 | 0.02% |

`/motion` alone accounts for 145 of the 156 directories: one per character or
creature, named `alb000`, `ang000`, `ark080`, `ash040` and so on, each holding
numbered `.nsbca` joint animations.

**A note on `/test`.** It is the fourth largest directory and it holds exactly
two files — `op.mods`, the opening video, and `ed.adx`, the ending song. Those
are not dead content; the directory name is the leftover, not what is in it.
The real test content is elsewhere and is counted in [09](09-leftovers.md).

---

## `EZBIND`

Two thirds of the cartridge's data is inside a container that is not a Nintendo
format and not any of the *Tales* envelopes the codec specification lists. It
announces itself:

```
+0x00  "EZBIND\0\0"
+0x08  u32  member count
+0x0C  u32  4 -- words per entry, and it is 4 on all 1,344 archives
+0x10  entry[count], sixteen bytes each:
         +0x00  u32  offset of the member's name, from the file start
         +0x04  u32  size of the member in bytes
         +0x08  u32  offset of the member, from the file start
         +0x0C  u32  a 32-bit tag
       name table -- NUL-terminated names, in entry order
       member data, each member aligned to four bytes
```

The class that reads it is in the ARM9's own type names: **`cEzArchiveWrapper`**
([09](09-leftovers.md)).

### The reading is checked, not assumed

Four claims, checked on every archive by `ezbind.py`: the name table begins
exactly where the entry array ends; every name offset lands inside it; the
members tile the file from the end of the name table to the last byte with no
overlap and no gap beyond four-byte padding; and the `+0x0C` tag is distinct
within an archive.

| | |
|---|---|
| files walked | 6,378 |
| `EZBIND` archives | **1,344** |
| …of which had to be decompressed first | **101** |
| archive bytes | 60,792,584 |
| members | **9,646** |
| member bytes | 60,416,314 |
| archives failing the structural check | **1** |

The one failure is `/battle/btleff.bin`, where the `+0x0C` tag repeats between
two members; everything else about it tiles correctly. Nothing else in 1,344
archives disagrees with the layout above.

The smallest archive on the cartridge is `/title/logoalfa.arc`, and it is worth
printing whole because it is the format in three lines:

```
logoalfa.nbfc   0x0000006C   11712   0x396F7638
logoalfa.nbfp   0x00002E2C     512   0x396F7645
logoalfa.nbfs   0x0000302C    1536   0x396F7648
```

11,712 bytes of tile data, a 512-byte 256-entry BGR555 palette and a 1,536-byte
screen map — the three files NitroSDK's `g2dcvtr` emits, under the developer's
own logo.

### The tag at `+0x0C`

Unidentified, and reported as such. It is distinct within an archive, it is not
the member's size, offset or index, and it is close but not equal between
members whose names differ only in their last character — `logoalfa.nbfc`,
`.nbfp` and `.nbfs` give `0x396F7638`, `0x396F7645` and `0x396F7648`, whose low
bytes differ by the same amounts as `c`, `p` and `s` do not. A name hash is the
obvious guess and nothing tried here reproduces it, so it is named a tag.
[99](99-open-questions.md).

### What is inside

The member census, by the extension the container itself gives each member:

| extension | members | bytes | what |
|---|---:|---:|---|
| `.nsbmd` | 1,683 | 37,145,808 | Nitro 3D models |
| `.nsbtx` | 787 | 9,129,448 | Nitro 3D textures |
| `.nsbca` | 1,586 | 7,750,624 | Nitro joint animations |
| `.dat` | 1,269 | 2,273,600 | collision and attribute data |
| `.imb` | 39 | 1,754,560 | in-house bitmaps (the ending sequence) |
| `.nsbta` | 1,057 | 1,115,604 | Nitro texture SRT animations |
| `.nbfc` | 517 | 722,752 | Nitro basic-format character data |
| `.mpb` / `.plb` | 39 + 39 | 103,424 + 19,898 | map and palette, beside the `.imb` |
| `.ntft` / `.ntfp` / `.nbfp` / `.nbfs` | 67 / 103 / 517 / 21 | 121,730 | textures, palettes, screens |
| `.boxtest` | 1,733 | 27,728 | sixteen bytes each — bounding boxes |
| `.layout`, `.ep`, `.pix`, `.nsbtp` | 148 | 190,531 | in-house, small |

Grouped the way [`formats.py`](../tools/formats.py) groups the top-level files,
so the two tables in [07](07-media-and-budget.md) mean the same thing:

| class | members | bytes | share |
|---|---:|---:|---:|
| 3D model | 1,683 | 37,145,808 | 61.48% |
| 3D texture | 787 | 9,129,448 | 15.11% |
| 3D animation | 2,673 | 8,884,476 | 14.71% |
| geometry / collision | 1,269 | 2,273,600 | 3.76% |
| other (in-house, unclassified) | 1,991 | 2,121,477 | 3.51% |
| 2D graphics | 1,241 | 848,322 | 1.40% |
| font | 1 | 8,228 | 0.01% |
| text | 1 | 4,955 | 0.01% |

### Nesting

`ezbind.py --walk` descends into members as well as into compressed wrappers.
**No archive contains another archive**: 9,646 members, zero of them `EZBIND`.
The nesting that does exist is one level of *compression* — 101 archives arrive
inside a BIOS `LZ77` stream and are `EZBIND` once decompressed. The rule
section 7 of the codec specification learned on *Tales of the Abyss* — do not
stop the census at the member level — applies here in that one direction and no
further.

---

## What is not here

`NARC`, Nintendo's own archive format, appears **zero** times in 134,217,728
bytes. Nor does any *Tales* envelope: `TLPS`, `AFS\0`, `SCPK`, `THEIRSCE`,
`FILE.FPB`, `FPS2`, `FPS3`, `FPS4`, `CVMH`, `ROFSBLD` are all zero, and the
`CPS ` and `CPS\0` of *Tales of Legendia*'s 2005 envelope return one hit each
against a chance rate of 0.031 — both inside field payload, neither followed by
a plausible size. `TLPK` returns three, `ADX` seventeen and `SLZ` eight, all at or
below the chance rate for their needle lengths on a medium this size, and the
three `TLPK` sit inside `/field/f023.bin`, `f025.bin` and `f026.bin` with no
container structure around them.
[`reports/magic-sweep.txt`](../reports/magic-sweep.txt) prints the rate beside
every count.

`ROFS`, CRI's own volume format, returns three hits and they are **not** noise
— but they are not a volume either. All three sit in overlay 1, in a table of
format-identifier strings next to `RIFF` and `criSsPly_Play`, which is the CRI
library naming the formats it can open. No `ROFS` volume, and no `ROFSBLD`
builder stamp, is on the cartridge.

The denominator matters and it is the opposite way round from a disc: a
four-byte needle expects **0.031** chance hits in 128 MB where the same needle
in a 4.36 GB DVD expects 1.01. A zero here is much stronger than a zero on
*Tales of the Abyss*, and a single hit is worth locating — which is why all of
them were.
