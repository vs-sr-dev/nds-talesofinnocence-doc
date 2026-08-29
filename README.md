# Tales of Innocence (Nintendo DS, 2007, Japan) — structural documentation

Reverse-engineering notes on the Japanese Nintendo DS release of *Tales of
Innocence* — game title **`TOIINNOCENCE`**, game code **`AYTJ`**, maker code
`AF`, ROM version `0x00`, one 128 MiB cartridge — published by Bandai Namco
Games and developed by **Alfa System**, which this cartridge, unlike its
predecessor, says itself.

This repository is **documentation and analysis only**. It contains no ROM, no
extracted asset, no executable, no patch and no translation. There is no
porting, BYOA or modding intent. Every number quoted was produced by running the
tools in [`tools/`](tools/) on an image supplied separately, and their output is
committed under [`reports/`](reports/) so the claims can be checked without
owning the cartridge.

It is the twelfth build in the
[tales-blockcodec-doc](https://github.com/vs-sr-dev/tales-blockcodec-doc)
corpus, the second on the Nintendo DS, and it exists to be the **control** that
[nds-talesofthetempest-doc](https://github.com/vs-sr-dev/nds-talesofthetempest-doc)
opened its own list of unanswered questions by asking for.

---

## TL;DR

*Tales of the Tempest* (Nintendo DS, 2006) has no *Tales* block codec, no BIOS
decompression, and no compression at all. But it changed **two variables at
once** — the machine and the developer — so its zero could not say which one it
was about, and no second DS image existed to run the identical probes over.

This is that second image. Same platform, same publisher, one year later, a
**third** studio outside the Namco Tales Studio line. Four outcomes were
possible and none was assumed. The answer:

| | Tempest, 2006 | **Innocence, 2007** | Hearts, 2008 |
|---|---|---|---|
| the *Tales* block codec | absent | **absent** | absent |
| 4078 / 4079 / 4070 / 4071 / 4080, either ARM encoding | 0 for four of them; six 4080 sites, four of them a 4,096-scaled cosine table | **0 — not one of the five, anywhere** | 0 for four; seven 4080 sites, four of them a 4,096-scaled cosine table again |
| modules, and how many were packed | 2, none packed | 5, none packed | **33, of which 32 `BLZ`-packed** |
| BIOS decompression wrappers linked / called | 12 / **0** | 12 / **0** | 6 / **0** |
| data in a BIOS compression format | **0 files of 4,712** | **106 of 6,378**, 102 of them `LZ77`, 16.9 MB → 32.1 MB | 11 files of 5,145 — but **5,280 streams inside the containers**, 61.7 MB → 123.2 MB |
| a container | none | **1,344 `EZBIND` archives, 9,646 members, 60.4 MB** | 2,492 `FPS4` archives and 1,508 `V154` objects |
| the whole image through deflate | 52.6% | **73.5%** | 78.24% |
| cartridge unused | **41.3%** | **3.2%** | 7.49% / 9.27% |
| media share | 13.22% | **51.40%**, with **2.81 hours of voice** | 51.39% / 49.61%, with **5 h 56 m of voice** |
| the developer named | nowhere | **three ways** | nowhere |

So the codec is absent from both, **and the platform is excluded as the
explanation.** A Nintendo DS *Tales* cartridge can compress, does compress, and
this one compresses in a format the DS itself defines — while licensing CRI for
audio and Actimagine's Mobiclip for video and writing its own container. What
Tempest's zero was about was not the machine.

What it is about is still not fully settled *on this machine*, and
[99](docs/99-open-questions.md) says so: both developers are outside the studio
line, so "the codec travels with that codebase" survives this cartridge
untouched. This repository asked for a title *from* that line and said there was
not one on the DS.

**A third cartridge has since been measured and it is the nearest thing to
one.** *Tales of Hearts* (Nintendo DS, 18 December 2008) carries the project tag
`TO9` — the number after *Tales of the Abyss*'s `TO7` and *Tales of Vesperia*'s
`TO8`, both line builds that carry the codec — and it does not carry the codec
either. But it **names its developer nowhere**, in any of three alphabets, and
was compiled with RTTI off, so it supplies a project number in the right place
and no hand attached to it. The question this repository asked is narrowed by
that cartridge and not closed by it.
[nds-talesofhearts-doc](https://github.com/vs-sr-dev/nds-talesofhearts-doc).

**It was answered off the DS.** *Tales of Symphonia: Ratatosk no Kishi* (Wii,
2008) is the direct sequel to the corpus's only PowerPC positive, from inside
the studio line, on a Nintendo console — and it carries no codec either, with
the strong byte test available for the first time across a console generation:
**10 bytes** of shared decoder against **835** of shared SDK code. So the
reading that the codebase had simply never shipped a Nintendo title is dead, and
the two zeros here are facts about their two studios.
[wii-talesofsymphoniadotnw-doc](https://github.com/vs-sr-dev/wii-talesofsymphoniadotnw-doc)

### Seven answers

**1. The constant scan is a clean zero, with no site to explain away.** Across
the ARM9, the ARM7 and all three overlays — **78,489** ARM data-processing
immediates, **140,305** THUMB instructions carrying a literal, **554,020**
aligned words, **27,469** PC-relative loads resolved to **22,262** distinct
targets — there is not one 4078, 4079, 4070, 4071 or 4080 in either encoding.
Tempest had six `4080` sites to disassemble; this has none.
[05](docs/05-block-codec.md)

**2. Nothing is compressed that would have hidden it.** Neither module and none
of the three overlays is packed, checked three independent ways — the overlay
table's flag, the ARM9's `compressed_static_end`, and each module's `BLZ`
footer. Two DS cartridges in, the linker's backwards `LZ` has still never been
used. [04](docs/04-executables.md)

**3. The structural probe agrees, and its ten hits are the ARM trap.** Zero
`orr rX,rX,#0xFF00` refills anywhere; zero 4,096-byte stack frames; and overlay
2's ten three-of-five sites are **22 THUMB `add #19` that are ARM words read at
even offsets** — `mov r3,r3,lsl r6`, the bit-consume step of the video decoder —
plus a 4/5/6-bit bitfield unpack. Genuine ARM count: zero, exactly as on
Tempest. [05](docs/05-block-codec.md)

**4. The DS BIOS is linked and never called, and the data is in its format
anyway.** Twelve wrappers, **40,411 distinct branch targets resolved across all
five modules**, **zero callers** — while `CpuSet` has one and `Stop/Sleep` seven.
No inline `svc` that is an instruction; no wrapper address anywhere as a data
word, so not a function pointer either. Meanwhile **102 files decode as BIOS
`LZ77`, consuming themselves exactly**. Where that decoder lives is
[the first open question](docs/99-open-questions.md), and it is stated as a
contradiction rather than smoothed over. [06](docs/06-what-it-uses-instead.md)

**5. `EZBIND`.** 1,344 archives holding 9,646 members and 60,416,314 bytes —
two thirds of the cartridge's data — in a container that is not Nintendo's, not
any *Tales* envelope, and named by the ARM9's own `cEzArchiveWrapper`. Sixteen
bytes of header, sixteen per member, and four structural claims checked on every
archive: 1,343 of 1,344 pass. [03](docs/03-file-system-and-containers.md)

**6. The cartridge carries a positive control for five decompressors, and it
found two defects in ours.** `/motion/alb000/` holds one 6,736-byte animation
shipped **five times over** — `LZ77`, `RLE`, 4-bit and 8-bit Huffman, and the
16-bit difference filter — beside the original. All five now decode to it byte
for byte, and getting there fixed a wrong Huffman leaf mask, a lost address
alignment, and the difference filters' type bytes.
[06](docs/06-what-it-uses-instead.md)

**7. `stan` and `dimlos` do not recur.** Tempest carries a field-character
family named for *Tales of Destiny*'s 1997 protagonist and a prop named for his
sword, and could not decide between "one team's placeholder" and "a series
convention". Over **13,950 distinct internal Nitro names in 6,664 model and
animation payloads**, `dimlos` occurs **zero** times in 134,217,728 bytes and
every one of the 23 `stan`/`Stan` hits is `charastand` or `Standard`. That is
the control Tempest lacked. [08](docs/08-cross-title.md)

### And the archaeology

**A Windows `dir` listing, shipped inside the game.** `/battle/list` is 14,109
bytes of captured `dir` output from **`D:\toi\resorce\archive`**, dated
**2006-12-05**, with the volume serial, 265 asset names and sizes — several of
them 16-byte empty placeholders — and 10.85 GB of free space. It is the only
Windows path on the cartridge and it gives the project's directory name, `toi`.

**A thousand class names.** The executables were built with RTTI on, so they
carry **1,047 C++ `type_info` names**: 584 beginning `Battle`, 147 `Effect`, 60
`Toi`, and **43 beginning `Mappy`** — a complete entity–component framework with
a factory, behaviours, collision shapes and a resource layer, in which *the
platform is a suffix*, `cMappyComponentDSStandardEntity`. That is what Alfa
System brought with it. Tempest names its developer nowhere at all.

**The credits as plain text.** `/staff/staff.bin` holds a 4,955-byte Shift-JIS
`list.txt` with the full Japanese voice cast, both KOKIA theme titles, and a
block headed `アルファ・システム　スタッフ` naming thirty people. Tempest
shipped its credits as 32 tile sets with no readable text at all — five *Tales*
builds, five different behaviours.

**Five boot logos.** `logonamco.arc`, `logobng.arc`, `logoalfa.arc`,
`logocri.arc`, `logoactimagine.arc` — the cartridge's whole supply chain, in
five 13 KB archives.

**Six dates from four independent sources.** Nine CRI middleware components
all stamped `Sep 28 2007 13:14:01`–`:11`; a save signature reading
`TOIBACKUP:2007/10/07`; the `dir` listing's `2006/12/05`; and asset-name groups
back to `050131`. There is no compiler build stamp — this cartridge has no
`__DATE__` anywhere, where Tempest had one.

**The whole world map is named after a test scene.** 196 of the 200 files in
`/world` are `f_test04_Room_00` … `_79`. They are not placeholders — they carry
real geometry and real internal names. [99](docs/99-open-questions.md)

---

## Claim status

| Claim | Status | Where |
|---|---|---|
| `TOIINNOCENCE` / `AYTJ` / `AF`, ROM version `0x00`, capacity `0x0A` = 134,217,728 | **Verified** — from the header, not from the file name | [02](docs/02-cartridge-and-header.md) |
| Header CRC `0xFF17` and logo CRC `0xCF56` both match, and the logo CRC is the retail value | **Verified** — recomputed | [02](docs/02-cartridge-and-header.md) |
| The secure-area CRC does not match, and none of three restorations recovers it | **Verified** | [02](docs/02-cartridge-and-header.md) |
| …and the region is decrypted SDK code in filler | *Consistent* — 17 wrappers in 2 KiB against 0 in 1,980 control windows | [02](docs/02-cartridge-and-header.md), [99](docs/99-open-questions.md) |
| Neither module and none of the three overlays is compressed | **Verified** — overlay flags, `ModuleParams` and the `BLZ` footer, three ways independently | [04](docs/04-executables.md) |
| 156 directories, 6,375 named files, 3 unnamed FAT entries and they are the overlays | **Verified** | [03](docs/03-file-system-and-containers.md) |
| The `EZBIND` layout, checked on every archive | **Verified** — 1,343 of 1,344 pass four structural claims | [03](docs/03-file-system-and-containers.md) |
| The `EZBIND` tag at `+0x0C` | *Open* — distinct per archive, not size/offset/index, no hash reproduces it | [99](docs/99-open-questions.md) |
| `4078` and `4079` cannot be ARM immediates; `4080` is `0xFF ror #28` | **Verified** — by construction, printed by the tool | [05](docs/05-block-codec.md) |
| Zero 4078 / 4079 / 4070 / 4071 / **4080**, both encodings, all five modules | **Verified** — with all five denominators per module | [05](docs/05-block-codec.md) |
| No structural fingerprint: 0 `orr #0xFF00`, 0 4,096-byte stack ring | **Verified** — with denominators | [05](docs/05-block-codec.md) |
| All 22 THUMB `add #19` in overlay 2 are ARM words misread as THUMB | **Verified** — the containing word printed for each | [05](docs/05-block-codec.md) |
| The three remaining overlay-2 sites are a 4/5/6-bit bitfield unpack in the video decoder | **Verified** — disassembled | [05](docs/05-block-codec.md) |
| The unmodified reference decoder finds no block anywhere | **Verified** — **23,083 payloads, 657,419,133 bytes, both dialects, 0 blocks**; the control in the same run returns **1,089** on the 1995 cartridge | [05](docs/05-block-codec.md) |
| Twelve BIOS decompression wrappers are linked and have 0 call sites | **Verified** — 40,411 branch targets, across the module boundary; `CpuSet` has 1, `Stop/Sleep` 7 | [06](docs/06-what-it-uses-instead.md) |
| …and no wrapper address appears as a data word, so not a function pointer either | **Verified** | [06](docs/06-what-it-uses-instead.md) |
| 102 files are BIOS `LZ77` streams, 16,901,069 → 32,116,356, 1.90× | **Verified** — each decodes and consumes its whole file | [06](docs/06-what-it-uses-instead.md) |
| Four more files are `RLE`, both Huffmans and the 16-bit difference filter | **Verified** — all four decode byte-for-byte to the original beside them | [06](docs/06-what-it-uses-instead.md) |
| The other six BIOS formats cannot be excluded by decoding, so they are reported by header count | **Verified** — with the reason | [06](docs/06-what-it-uses-instead.md) |
| **Where the `LZ77` decoder is** | *Open* — five fingerprint families over five modules, every hit read, nothing found | [99](docs/99-open-questions.md) |
| The cartridge deflates to 73.47%; already-`LZ77` containers to 91.27% and raw ones to 52.23% | **Verified** | [06](docs/06-what-it-uses-instead.md) |
| 3.20% of the cartridge unused, every byte `0xFF` | **Verified** | [02](docs/02-cartridge-and-header.md) |
| Media 51.40% of the cartridge; models 61.48% of container bytes | **Verified** — classified by magic and arithmetic, never by extension | [07](docs/07-media-and-budget.md) |
| 2,444 CRI streams, 56,208,162 bytes, 2.86 hours; `/voice` alone 2.81 hours | **Verified** for the count and bytes; the AHX duration is the header's arithmetic | [07](docs/07-media-and-budget.md), [99](docs/99-open-questions.md) |
| 310 `STRM` at 396.8 s and 819 `SWAV` at 426.0 s; the music is sequenced | **Verified** — rates cross-checked against the DS sound clock | [07](docs/07-media-and-budget.md) |
| One Mobiclip video, 2,136 frames at 256 × 192 with 32,000 Hz audio | **Verified** | [07](docs/07-media-and-budget.md) |
| No duration is quoted for the video | *Open* — no frame-rate field is identified | [99](docs/99-open-questions.md) |
| Nine CRI components stamped 2007-09-28 13:14:01–13:14:11 | **Verified** | [02](docs/02-cartridge-and-header.md) |
| `TOIBACKUP:2007/10/07` in the ARM9's save signature | **Verified** | [02](docs/02-cartridge-and-header.md) |
| `/battle/list` is a Windows `dir` of `D:\toi\resorce\archive`, 2006-12-05 | **Verified** | [09](docs/09-leftovers.md) |
| 1,047 C++ type names, 43 of them a framework called `Mappy` | **Verified** — length-prefixed, so the scan is exact | [04](docs/04-executables.md), [08](docs/08-cross-title.md) |
| `cEzArchiveWrapper` names the container | **Verified** | [04](docs/04-executables.md) |
| No corpus envelope, tag or *Tales* project tag above its chance rate | **Verified** — with the chance rate beside every count, and every four-byte hit located | [08](docs/08-cross-title.md) |
| `dimlos` occurs 0 times; all 23 `stan`/`Stan` hits are `charastand` or `Standard` | **Verified** — each read | [08](docs/08-cross-title.md) |
| …so Tempest's `stan` / `dimlos` are not a series convention | *Consistent* — the simpler reading, not proved | [08](docs/08-cross-title.md) |
| `cTolWorldShip` — one `Tol` among sixty `Toi` | **Verified** as present; *Open* as to whether it is a typing slip | [99](docs/99-open-questions.md) |
| The developer is named in the credits text and in a boot-logo file name | **Verified** | [09](docs/09-leftovers.md) |
| 197 files and 2,769,424 bytes of genuine test content, 98% of it `/world/f_test04_*` | **Verified** | [09](docs/09-leftovers.md) |
| 4,591 file names are not spelled out anywhere outside the name table | **Verified** as a count; *not* a count of unused files | [07](docs/07-media-and-budget.md), [99](docs/99-open-questions.md) |
| The world map is named after a test scene | **Verified** as present; *Open* as to why | [99](docs/99-open-questions.md) |
| The platform is excluded as the explanation for Tempest's zero | **Verified** — this cartridge compresses, in the platform's own format | [05](docs/05-block-codec.md) |
| The *codebase* remains the surviving reading | **Confirmed in 2008** — a Wii build *from* the line returns the same zero, so the alternative is dead | [99](docs/99-open-questions.md) |

---

## Documents

| | |
|---|---|
| [01 — Overview](docs/01-overview.md) | what this is, why it was opened, and the highlights |
| [02 — The cartridge and its header](docs/02-cartridge-and-header.md) | every header field, the three CRCs, the secure area, the budget of the medium, and every date |
| [03 — The file system and the container](docs/03-file-system-and-containers.md) | 6,378 FAT entries, 156 directories, and `EZBIND` taken apart and checked |
| [04 — The executables](docs/04-executables.md) | two modules, three overlays, the decompression check, and 1,047 class names |
| [05 — The block codec](docs/05-block-codec.md) | the measurement this repository exists for, with all its denominators |
| [06 — What it uses instead](docs/06-what-it-uses-instead.md) | the BIOS formats without the BIOS, CRI, Actimagine, and one unlocated decoder |
| [07 — Media and the budget](docs/07-media-and-budget.md) | 2.81 hours of voice, one video, and where every byte went |
| [08 — Cross-title](docs/08-cross-title.md) | inwards to the other *Tales*, outwards to Alfa System |
| [09 — Leftovers](docs/09-leftovers.md) | a shipped `dir` listing, a five-format benchmark, and the credits as text |
| [99 — Open questions](docs/99-open-questions.md) | eleven of them, each with the measurement beside it |

## Reports

Every number in the documents comes from a committed tool whose output is
committed too, under [`reports/`](reports/). The commands that produce each one
are in [tools/README.md](tools/README.md).

## Tools

Python 3, standard library only, one file per job. Eleven came from
[nds-talesofthetempest-doc](https://github.com/vs-sr-dev/nds-talesofthetempest-doc)
and **five had to be extended**; each extension names something Tempest did not
have — a directory tree, an overlay, a container, a middleware audio format, and
a real Huffman stream. [tools/README.md](tools/README.md) lists them.
`tales_block.py` is copied unmodified from the corpus, md5
`e2dcd6b8dc717b84f67bf8a46568298c`.

## Related

* [tales-blockcodec-doc](https://github.com/vs-sr-dev/tales-blockcodec-doc) — the format specification and the corpus
* [nds-talesofthetempest-doc](https://github.com/vs-sr-dev/nds-talesofthetempest-doc) — the other Nintendo DS cartridge, and the one this controls
* [ps2-talesoftheabyss-doc](https://github.com/vs-sr-dev/ps2-talesoftheabyss-doc) · [ps2-talesoflegendia-doc](https://github.com/vs-sr-dev/ps2-talesoflegendia-doc) · [ps2-talesofrebirth-doc](https://github.com/vs-sr-dev/ps2-talesofrebirth-doc) · [ps2-talesofdestiny2-doc](https://github.com/vs-sr-dev/ps2-talesofdestiny2-doc)
* [gc-talesofsymphonia-doc](https://github.com/vs-sr-dev/gc-talesofsymphonia-doc) · [ps1-talesofeternia-doc](https://github.com/vs-sr-dev/ps1-talesofeternia-doc) · [ps1-talesofdestiny-doc](https://github.com/vs-sr-dev/ps1-talesofdestiny-doc) · [snes-talesofphantasia-doc](https://github.com/vs-sr-dev/snes-talesofphantasia-doc)
* [keitai-talesoftactics-doc](https://github.com/vs-sr-dev/keitai-talesoftactics-doc) · [android-talesofcrestoria-doc](https://github.com/vs-sr-dev/android-talesofcrestoria-doc)

## Licence

Tools under [MIT](LICENSE). Documents and reports under
[CC BY 4.0](LICENSE-DOCS). No game data of any kind is included.
