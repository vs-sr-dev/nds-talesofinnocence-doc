# 01 — Overview

*Tales of Innocence*, Nintendo DS, Japan, 2007. Published by Bandai Namco
Games, developed by Alfa System — and unlike the cartridge this repository
exists to control, **this one says so itself**, in Shift-JIS, in a text file it
ships ([09](09-leftovers.md)).

Everything below is read from the image's own structures: the NDS header at
offset 0, the file name and allocation tables, the overlay table, the module
parameters, and the payloads. Nothing is taken from the dump's file name or
from a catalogue.

---

## Why this cartridge was opened

The [tales-blockcodec-doc](https://github.com/vs-sr-dev/tales-blockcodec-doc)
corpus tracks one in-house LZSS codec across eleven builds and six platforms.
The eleventh, *Tales of the Tempest* (Nintendo DS, 2006), returned a negative
that **could not say what it was a negative about**: the machine changed and
the developer changed in the same step, and there was no second Nintendo DS
image to run the identical probes over. Its own
[99-open-questions](https://github.com/vs-sr-dev/nds-talesofthetempest-doc/blob/main/docs/99-open-questions.md)
opens with that admission.

This is the control. Same platform, one year later, a **third** studio — Alfa
System, which descends neither from the Wolf Team / Namco Tales Studio line nor
from Tempest's developer. Four outcomes were possible and none was assumed.
What came back is the fourth one, and it is the most informative of them.

---

## The answer, in one table

| | *Tales of the Tempest*, 2006 | *Tales of Innocence*, 2007 |
|---|---|---|
| the *Tales* block codec | **absent** — 0 blocks in 9,055 payloads | **absent** — 0 blocks in **23,083 payloads, 657,419,133 bytes** |
| 4078 / 4079 / 4070 / 4071 / 4080, either ARM encoding | 0 for four of them; **six 4080 sites**, four of them entries of a 4,096-scaled cosine table | **0 — not one of the five, anywhere** |
| BIOS decompression wrappers linked | 12 | 12 |
| …with a caller | **0** | **0** |
| data in a BIOS compression format | **0 files of 4,712** | **106 files of 6,378**, 102 of them `LZ77` |
| a container | none | **1,344 `EZBIND` archives, 9,646 members** |
| the whole image through deflate | **52.6%** | **73.5%** |
| cartridge unused | **41.3%** | **3.2%** |
| middleware named | Actimagine `VX` | Actimagine **Mobiclip**, and **nine CRI components** |
| the developer named | nowhere | **in the credits, in the boot logos, in the class names** |

So the two DS cartridges agree on the thing the corpus asked about — neither
carries the codec, and neither calls the BIOS — and they disagree about almost
everything else. Tempest stored its data raw. Innocence compresses 13% of
its file bytes in the platform's own `LZ77` format, wraps two thirds of them in
a container of its own, and buys its audio and video from two middleware
vendors.

The consequence for the corpus is in [05](05-block-codec.md) section 6 and it
is worth stating here: **the boundary is not the Nintendo DS.** A DS cartridge
can compress, does compress, and this one compresses in a format the DS itself
defines. What Tempest's zero was about was Tempest.

---

## What is here

| | |
|---|---|
| [02 — the cartridge and its header](02-cartridge-and-header.md) | every header field, the three CRCs, the secure area, and where the 128 MiB went |
| [03 — the file system and the container](03-file-system-and-containers.md) | 6,378 FAT entries, 156 directories, and `EZBIND` taken apart and checked |
| [04 — the executables](04-executables.md) | two modules, three overlays, none compressed, and the 1,047 class names they kept |
| [05 — the block codec](05-block-codec.md) | the measurement this repository exists for, with all its denominators |
| [06 — what it uses instead](06-what-it-uses-instead.md) | the BIOS formats without the BIOS, CRI, Actimagine, and one unlocated decoder |
| [07 — media and the budget](07-media-and-budget.md) | 2.81 hours of voice, one video, and where every byte went |
| [08 — cross-title](08-cross-title.md) | inwards to the other *Tales*, outwards to Alfa System |
| [09 — leftovers](09-leftovers.md) | a shipped `dir` listing, a five-format benchmark, and the credits as text |
| [99 — open questions](99-open-questions.md) | eleven of them, each with the measurement beside it |

Every number in the documents is reproduced by a tool in [`tools/`](../tools)
whose output is committed under [`reports/`](../reports). The commands are in
[tools/README.md](../tools/README.md).

---

## Highlights

**The codec is not here, and this time the zero is clean.** Across the ARM9,
the ARM7 and all three overlays — 78,489 ARM data-processing immediates,
140,305 THUMB instructions carrying a literal, 554,020 aligned words, and
27,469 PC-relative loads resolved to 22,262 distinct targets — there is **not
one 4078, 4079, 4070, 4071 or 4080 in either encoding**. Tempest had five 4080
immediates and one unreferenced 4080 word to account for; this cartridge has
nothing to explain away.

**The DS BIOS decompression services are linked and never called, and the data
is in their format anyway.** Twelve wrappers across the two processors, 40,411
distinct branch targets resolved, **zero callers** — while `CpuSet` has one and
`Stop/Sleep` seven, so the instrument finds callers where there are callers.
And no wrapper's address appears as a data word anywhere, so it is not reached
through a function pointer either. Meanwhile **102 files decode as BIOS `LZ77`,
consuming themselves exactly**: 16,901,069 bytes on the cartridge becoming
32,116,356, a ratio of 1.90×. Where the code that reads them lives is
[the first open question](99-open-questions.md).

**The cartridge carries a positive control for five decompressors, and it found
two defects in ours.** `/motion/alb000/` holds one animation shipped **five
times over** — `LZ77`, `RLE`, 4-bit Huffman, 8-bit Huffman and the 16-bit
difference filter — beside the original `.nsbca`. All five now decode to it
byte for byte, and getting there fixed a wrong leaf mask and a lost address
alignment in `ndscomp.py`'s Huffman, and moved the difference filters from
`0x80`/`0x81` to their real type bytes `0x81`/`0x82`. Nobody in this corpus had
a stream to check those against before ([06](06-what-it-uses-instead.md)).

**`EZBIND`.** Where Tempest had 4,712 files in one flat directory and no
container at all, this cartridge has **1,344 `EZBIND` archives holding 9,646
members and 60,416,314 bytes**, and 101 of them sit inside an `LZ77` stream.
The format is sixteen bytes of header and sixteen per member, and every claim
about it is checked on every archive: 1,343 of 1,344 pass ([03](03-file-system-and-containers.md)).

**It names its developer three ways.** The credits ship as **plain Shift-JIS
text** and read `アルファ・システム　スタッフ`; the boot sequence has
`logoalfa.arc` next to `logonamco`, `logobng`, `logocri` and `logoactimagine`;
and the executables were built with RTTI on, so they carry **1,047 C++ class
names** — including the framework the studio brought with it (`Mappy`, 43
classes) and the one that names the container (`cEzArchiveWrapper`). Tempest
named its developer nowhere at all ([09](09-leftovers.md), [08](08-cross-title.md)).

**Six dates, from four independent sources.** Nine CRI middleware components
all stamped `Sep 28 2007 13:14:01`–`:11`; a save-file signature reading
`TOIBACKUP:2007/10/07`; a Windows `dir` listing of `D:\toi\resorce\archive`
dated `2006/12/05`, shipped inside the game as `/battle/list`; and three
`yymmdd` groups in asset names, the oldest `050131` ([02](02-cartridge-and-header.md)).

**The budget is nothing like Tempest's.** Audio is **48.38% of the cartridge**
— 2,444 CRI streams, **2.81 hours of voice** — against Tempest's eleven minutes
twelve seconds. Video is one Actimagine **Mobiclip** file. Containers are
33.96%, and inside them 3D models are 61.48% of the member bytes. **3.2% of the
cartridge is unused**, all of it `0xFF`, against Tempest's 41.3%
([07](07-media-and-budget.md)).

**`stan` and `dimlos` do not recur.** Tempest carries a field-character family
named after *Tales of Destiny*'s 1997 protagonist and a prop model named after
his sword, and its own open questions could not decide whether that was one
team's placeholder or a series convention. Over **13,950 distinct internal
Nitro names in 6,664 model and animation payloads** here, `dimlos` occurs
**zero** times in 134,217,728 bytes and every `stan` is `charastand` or
`Standard` ([08](08-cross-title.md)). That is a control Tempest did not have,
and it is fed back to that repository.
