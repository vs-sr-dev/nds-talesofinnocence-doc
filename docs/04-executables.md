# 04 — The executables

[`ndsrom.py`](../tools/ndsrom.py), [`ndscomp.py`](../tools/ndscomp.py),
[`disarm.py`](../tools/disarm.py), [`symbols.py`](../tools/symbols.py).
[`reports/nds-overlays.txt`](../reports/nds-overlays.txt),
[`reports/symbols.txt`](../reports/symbols.txt).

---

## Five modules

| | ROM offset | size | RAM | compressed |
|---|---:|---:|---|---|
| `arm9.bin` | `0x00004000` | 676,952 | `0x02000000` | **no** |
| `arm7.bin` | `0x001FAA00` | 159,160 | `0x02380000` | **no** |
| overlay 0 (FAT file 0) | | 712,800 | `0x02120E60` | **no** |
| overlay 1 (FAT file 2) | | 577,312 | `0x02120E60` | **no** |
| overlay 2 (FAT file 1) | | 89,856 | `0x02120E60` | **no** |

All three overlays load at the **same** address, so they are mutually
exclusive: one is resident at a time on top of a 1,183,840-byte static ARM9
image. Their `bss` sizes are 224, 159,872 and 160 bytes.

### The decompression check comes first, and it is done three ways

Section 7 of the codec specification is emphatic about this: a constant scan
over a still-compressed module returns zero and looks exactly like a clean
negative, so the check has to happen before the scan, every time. On this
cartridge it was done three independent ways and all three agree:

1. the **overlay table's** compressed flag is `0` on all three entries, and its
   compressed-size field equals the plain size;
2. the ARM9's **`ModuleParams`**, at file offset `0xBA4`, has
   `compressed_static_end = 0x00000000`;
3. the **`BLZ` footer** of each of the five modules has a length delta of zero,
   which is how a module that was never packed says so —
   `ndscomp.py --blz` prints exactly that.

So the same thing that was true on *Tales of the Tempest* is true here: the
linker's backwards `LZ` was available and was not used, and the `BLZ` path in
`ndscomp.py` still has not been exercised against a real compressed module by
this corpus. That is worth saying plainly rather than leaving implicit — two
DS cartridges in, the code that exists to prevent a false negative has never
had to prevent one.

### The instruction mix

Innocence is a much more THUMB-weighted build than Tempest, which matters only
because it changes what a scan's denominators look like:

| | ARM data-processing immediates | THUMB instructions carrying a literal |
|---|---:|---:|
| Tempest ARM9 | 85,036 | 53,575 |
| **Innocence ARM9** | **22,568** | **43,310** |
| Innocence overlay 0 | 22,350 | 56,540 |
| Innocence overlay 1 | 18,419 | 30,972 |
| Innocence overlay 2 | 3,270 | 4,230 |
| Innocence ARM7 | 11,882 | 5,253 |

Overlay 2 is the exception in the other direction: it is almost entirely ARM,
and it is where the video decoder lives ([06](06-what-it-uses-instead.md)).

---

## What each module is

Read off the strings, the class names and the code, not off a guess.

**`arm9.bin`** — the resident engine. The NitroSDK system-call wrapper table at
`0x02000074`–`0x02000780`, the file system, the heap, the 3D scene graph, the
task manager, the save format, and the wireless code. It carries the SDK
component list, and the whole of it is two entries:

```
[SDK+NINTENDO:BACKUP]
[SDK+Actimagine:MO]
```

Tempest's read `[SDK+Actimagine:VX]` and `[SDK+NINTENDO:BACKUP]`. Same two
vendors, one generation apart on the video side: `VX` there, **`MO`** —
Mobiclip — here.

**`arm7.bin`** — the sound and input processor. Twenty-four SDK wrappers,
`SoundBias` three times, the DS sound driver. It contains **no** C++ type names
at all, which is consistent with it being C.

**overlay 0**, 712,800 bytes — **battle**. 739 of the cartridge's 1,047 class
names are here and 584 of them begin `Battle`: `cBattleChara_Ricardo`,
`cBattleActionRicardo_Groundasher`, `iBattleCharaController`,
`cBattleSemiAutoController`. 147 more begin `Effect`.

**overlay 1**, 577,312 bytes — **field, world and the CRI middleware**. This is
where the nine CRI build strings live ([02](02-cartridge-and-header.md)), and
where the `Mappy` framework's 43 class names live ([08](08-cross-title.md)).

**overlay 2**, 89,856 bytes — **title screen and video**. Twelve class names,
including `cToiMovie` and `cToiMovieFrameUpdate`, the cartridge's whole file
name table repeated as a string list, and — in ARM, heavily unrolled — a
bit-reader driven by a twelve-bit lookup table. That is the Mobiclip decoder;
[06](06-what-it-uses-instead.md) reads it.

---

## 1,047 class names

The single most useful thing about these executables, and the sharpest contrast
with the previous cartridge, is that they were **built with RTTI on**. The ARM
C++ ABI stores a `type_info` name as the length of the identifier in decimal
followed by the identifier, so

```
31cMappyComponentDSStandardEntity\0
```

is a class called `cMappyComponentDSStandardEntity`, and the decimal prefix is
what makes the scan exact rather than a guess: a run of letters after a number
is only accepted when the number is its length.
[`symbols.py`](../tools/symbols.py) does that and nothing else.

| module | names |
|---|---:|
| `arm9.bin` | 154 |
| `arm7.bin` | **0** |
| overlay 0 | 739 |
| overlay 1 | 142 |
| overlay 2 | 12 |
| **total** | **1,047** |

Grouped by the first capitalised word after the ABI's `c` (concrete) or `i`
(interface) prefix, which this codebase uses consistently:

| group | names | where |
|---|---:|---|
| `Battle` | 584 | overlay 0, arm9 |
| `Effect` | 147 | overlay 0 |
| `Toi` | 60 | arm9, overlay 1, overlay 2 |
| `DS` | 50 | arm9 |
| **`Mappy`** | **43** | overlay 1 |
| `Mn` (menu) | 31 | arm9, overlay 1 |
| `Effect2` | 16 | overlay 1 |
| `Cut` | 12 | overlay 1 |
| `3DScene` | 9 | arm9 |
| `Shop` | 8 | overlay 1 |
| `Title` | 7 | overlay 2 |
| `Subdisplay` | 6 | arm9 |

*Tales of the Tempest* has **no symbol table, no `.comment`, no company string
and no source path**, and its repository says so as a limitation on everything
it concludes about who built it. This cartridge has a thousand class names, and
three of the groups above are load-bearing:

* **`Toi`** — the project's own tag, `cToiWorld`, `cToiDungeon`, `cToiMovie`,
  `cToiBackupFile`. It matches the `D:\toi\resorce\archive` path in the shipped
  directory listing ([09](09-leftovers.md)).
* **`Mappy`** — a scene-graph, component, collision and resource framework, 43
  classes, none of which mentions *Tales* or `Toi`. This is what the studio
  brought with it, and [08](08-cross-title.md) takes it seriously.
* **`Ez`** — exactly one class, `cEzArchiveWrapper`, and it names the container
  that holds two thirds of the cartridge's data ([03](03-file-system-and-containers.md)).

One more, and it is small and odd. Among the `cToiWorld*` classes in overlay 1
there is a **`cTolWorldShip`** — `Tol`, not `Toi`, one key to the left on a
Japanese keyboard and also *Tales of Legendia*'s project tag. It is a single
name in 1,047 and the likeliest explanation is a typing slip; it is recorded
in [08](08-cross-title.md) with that stated, because a hit that is probably a
typo is still a hit and burying it would be the wrong habit.

---

## What the executables do not carry

* no `__DATE__` / `__TIME__` build stamp, in either module or any overlay;
* no compiler `.comment` string;
* no company name — `Alfa`, `ALFA`, `Namco`, `NAMCO`, `Bandai` and `BANDAI` are
  **zero** hits across all five modules and across the whole cartridge, and the
  studio's name reaches the image only through a boot-logo *file name* and
  through the credits *text* ([09](09-leftovers.md));
* no absolute source path in code — the one Windows path on the cartridge is in
  a data file, not in an executable.

So the class names are the whole of the code-side provenance, and they are a
great deal more than Tempest had.
