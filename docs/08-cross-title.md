# 08 — Cross-title, both directions

[`crosstitle.py`](../tools/crosstitle.py), [`magic_sweep.py`](../tools/magic_sweep.py),
[`symbols.py`](../tools/symbols.py).
[`reports/cross-title.txt`](../reports/cross-title.txt),
[`reports/magic-sweep.txt`](../reports/magic-sweep.txt),
[`reports/symbols.txt`](../reports/symbols.txt).

Every count below is printed with the number of bytes it was drawn from and the
expected number of chance hits at that needle length. On 134,217,728 bytes a
four-byte needle expects **0.031** chance hits and a three-byte needle expects
**8.0**, so a three-byte count in single figures means nothing and a four-byte
count of one is worth locating. That is the opposite way round from a DVD,
where the same four-byte needle expects 1.01, and it is why the zeros here are
strong.

---

## Inwards: does it carry anything from the other *Tales*?

**No.** And this is the direction that most needed a clean answer, because
Tempest's did not come out clean.

### The measurement that had to be extended

*Tales of the Tempest* kept every model in a file of its own, so reading the
top-level `.nsb*` files harvested every internal name on the cartridge — 7,337
distinct names across 2,410 files, and that pass is what produced its `stan` and
`dimlos` findings. Here almost every model is a **member of an `EZBIND`
archive**, and 101 of those archives are inside an `LZ77` stream. Run unchanged,
the pass reads 1,516 loose `.nsbca` files and reports 936 names as if that were
the corpus. Extended to descend through both layers, it reads **6,664 Nitro
payloads and 13,950 distinct internal names** — nearly twice Tempest's, from a
cartridge nearly twice the size.

That difference is the finding as much as the result is: on a cartridge with
containers, the name harvest has to go through them or it measures a fifth of
the data and says nothing about it.

### `stan` and `dimlos`

*Tales of the Tempest* carries a complete field-character asset family named
`stan` — the name of *Tales of Destiny*'s 1997 protagonist — and a single prop
model named `dimlos`, his sword. Its own open questions could not decide
between two readings: one team's prototyping placeholder, or a convention of
the series. A second DS *Tales* cartridge from an unrelated studio is exactly
the test.

| needle | hits in 134,217,728 bytes | what they are |
|---|---:|---|
| `dimlos` | **0** | — |
| `Dimlos` | **0** | — |
| `DIMLOS` | **0** | — |
| `ディムロス` | **0** | — |
| `stan` | 16 | **all** `charastand.arc` / `chara_stand%02d.nbfc`, plus one FNT entry |
| `Stan` | 7 | **all** `DS3DStandardNode`, `3DScenePrimitiveStandard`, `MappyStandardComponent` … |
| `STAN` | 0 | — |

Every one of the 23 was located and read. There is no `stan` character, no
`dimlos` prop, and 13,950 internal Nitro names contain neither.

**The reading.** `stan` and `dimlos` do not recur on a second Nintendo DS
*Tales* cartridge from a different studio. That does not prove they were a
placeholder on Tempest — a convention can be followed by one team and not
another — but it removes the only version of the "series convention" reading
that was testable from outside that cartridge, and it makes the placeholder
reading the simpler one. This is fed back to
[nds-talesofthetempest-doc](https://github.com/vs-sr-dev/nds-talesofthetempest-doc).

### Everything else, inwards

Character names from the other titles, in every capitalisation:

* `MINT` 2, `suzu` 2, `SUZU` 4, `tear` 2, `Norma` 1 — four-byte and five-byte
  needles at or barely above a 0.031 chance rate, all inside binary payload;
* `rid` 18, `RID` 15, `ras` 27, `RAS` 16, `guy` 6, `GUY` 11, `mao` 5, `MAO` 14,
  `jay` 8, `JAY` 12 — three-byte needles against a chance rate of **8.0**, so
  these are the noise floor;
* `Chat` 783 — the `/facechat` directory;
* the two matches inside internal Nitro names are `m040_bridge` (for `rid`) and
  `m002_grass` (for `ras`). Substrings of English words in map asset names.

Project tags: `TO7` 7, `TO8` 2, `ToR` 7, `ToL` 7, `tox` 9, `TOP` 18, `TOD` 7,
`TOE` 11, `TOS` 17, `TOT` 45, `ToT` 20 — every one a three-byte needle at or
below 8.0. `tor_`, *Tales of Rebirth*'s sound-effect prefix that turned up 109
times on *Tales of the Abyss*, returns **zero**, as does `no_se_`. `ToD2`
returns zero.

Containers: `TLPS`, `AFS\0`, `SCPK`, `THEIRSCE`, `FILE.FPB`, `FPS2`, `FPS3`,
`FPS4`, `CVMH`, `ROFSBLD`, `MSCF`, `NARC`, `VAGp`, `SAMPLE_GAME_TITLE` — all
**zero**. `CPS ` and `CPS\0`, *Tales of Legendia*'s 2005 envelope, return one
each; both were located, both sit inside `/field` payload, neither has a
plausible size behind it.

**One hit is worth its own paragraph**, because burying it would be the wrong
habit. Among overlay 1's `cToiWorld*` classes there is a **`cTolWorldShip`** —
`Tol`, not `Toi`. `ToL` is *Tales of Legendia*'s project tag, and `i` and `l`
are adjacent nowhere on a keyboard but are one pixel apart in most fonts. It is
one name in 1,047, there is no other `Tol` anywhere on the cartridge, and there
is no Legendia asset, tag or format here for it to belong to. The likeliest
explanation by a wide margin is a typing slip in a class name; it is recorded
because it is a real hit and the alternative reading, however thin, is the
reader's to weigh.

**So this is a clean cartridge, inwards** — the third that is clean, after
*Rebirth* and *Legendia*, with *Tempest* nearly so and *Abyss* not at all. It is
the first whose cleanliness was established with the name harvest run *through*
a container, which is a different and larger measurement than the ones before
it.

---

## Outwards: what did Alfa System bring?

This is the direction that came back **completely empty** on *Tales of the
Tempest* — no company string anywhere, no symbol table, no source path, and one
project-shaped tag (`NT_DS1`) surviving only inside an unconverted 3ds Max
intermediate. Here it is the richest section of the repository, and the reason
is one build setting: RTTI was left on ([04](04-executables.md)).

### `Mappy` — 43 classes, and it is not a *Tales* framework

Overlay 1 carries a complete scene framework whose every class begins `Mappy`:

```
iMappyComponent                    iMappyFactory
cMappyScene                        cMappyDSFactory
cMappyStandardComponent            cMappyDSCharaComponent
iMappyComponentEntity              cMappyComponentName
cMappyComponentBehavior            cMappyComponentDSBehaviorMotion
cMappyComponentDSBehaviorWaiting   iMappyComponentBehaviorFactory
iMappyComponentCollision           cMappyComponentCollisionDSSphere
cMappyComponentCollisionDSBoundingBox
cMappyComponentCollisionDSFloorMesh
cMappyComponentCollisionDSAttributeMesh
iMappyComponentCollisionDSAttributeMeshRandomizedPositionListener
iMappyConflict                     cMappyConflictDSPoint
cMappyConflictDSAttributeMesh      cMappyConflictDummy
iMappyDSResource                   cMappyDSStandardResource
cMappyDSWorldmapResource           cMappyDSEncountSymbolResource
cMappyDSTexture                    cMappyDSWorldmapTexture
cMappyDSSceneChara                 cMappyDSSceneEffect
...
```

Read the naming and the architecture is legible without any outside knowledge:
an entity–component system with a factory, named components, behaviours,
collision shapes, a "conflict" (collision-resolution) layer, and a resource
layer — and **the platform is a suffix, not a prefix**. `cMappyComponent` is
the abstract thing; `cMappyComponentDSStandardEntity` is the Nintendo DS
implementation of it. A framework written that way has been, or is expected to
be, compiled for something that is not a DS.

Not one of the 43 mentions `Toi`, `Tales`, or anything from this game. The
project-specific classes sit *on top* of them —
`cToiDungeonObjectFileLoadListener`, `cToiWorldEncountSymbolLottery` — and use
them.

`Mappy` returns **43 hits in the whole image**, against a chance rate of
0.00012 for a five-byte needle, and all 43 are these class names. `MAPPY` and
`mappy` return zero.

### `Ez` — the container's own class

Exactly one class name in 1,047 begins `Ez`, and it is **`cEzArchiveWrapper`**,
in the ARM9. `EzArchive` occurs once in 134,217,728 bytes against a chance rate
of 2.8 × 10⁻¹⁴. It names the `EZBIND` container of
[03](03-file-system-and-containers.md), which holds two thirds of the
cartridge's data and is not a Nintendo format, not a *Tales* format, and not
one this corpus has seen before.

So the answer to "what does the studio bring with it" is concrete and it is two
things: **a component framework called `Mappy` and an archive format called
`EZBIND`**, neither of which has anything to do with *Tales*.

### The company itself

| needle | hits | chance |
|---|---:|---|
| `Alfa System` / `ALFA SYSTEM` / `AlfaSystem` / `alfasystem` | **0** | 4×10⁻¹⁹ |
| `Namco` / `NAMCO` / `Bandai` / `BANDAI` | **0** | ≤5×10⁻⁷ |
| `Actimagine` | **1** | 1×10⁻¹⁶ |
| `CRI ` | 1 | 0.031 |
| `logoalfa` (in the file name table) | — | not a chance event |
| `アルファ・システム` (in the credits text) | — | not a chance event |

The Roman-alphabet company names are absent from the executables entirely, and
that part is the same as Tempest. What is different is that **the developer is
named twice in the data**: `/title/logoalfa.arc` sits in the boot sequence
beside `logonamco.arc`, `logobng.arc`, `logocri.arc` and `logoactimagine.arc`,
and the credits — shipped as plain Shift-JIS text, not as images — carry a
block headed `アルファ・システム　スタッフ` with thirty named people under
it ([09](09-leftovers.md)).

Five boot logos is itself a small result: the cartridge announces Namco, Bandai
Namco Games, Alfa System, CRI and Actimagine before it starts, which is the
whole of its supply chain in five archives of about 13 KB each.

### Other Alfa System titles

Searched for and absent: `Tengai`, `Gungrave`, `Hakuoki`, `Sting`, `Matrix` —
all zero. Nothing on this cartridge names another game. The studio's presence
here is the framework and the container, not shared content.

---

## The comparison the corpus asked for

| build | what it does with other titles' material |
|---|---|
| *Tales of Rebirth*, 2004 | the first clean disc; the whole cast romanised in English |
| *Tales of Legendia*, 2005 | clean; no cast names in English at all |
| *Tales of the Abyss*, 2005 | **not** clean — 109 sound effects prefixed `tor_`, three battle models named for the 1997, 2000 and 2002 protagonists; the tracklist in English, no cast |
| *Tales of the Tempest*, 2006 | nearly clean — `stan` and `dimlos`; credits shipped as 32 tile sets, **no readable text at all** |
| **Tales of Innocence, 2007** | **clean**; credits shipped as **plain Shift-JIS text**, full Japanese cast, and the developer named |

Four behaviours in five builds, and Innocence adds the fifth: the only one of
them that ships its credits as text a reader can extract in one line. Whatever
each of these choices measures, it is not a series policy — it is per build, and
on the two DS cartridges it is opposite.
