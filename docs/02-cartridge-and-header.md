# 02 — The cartridge and its header

Everything here is read by [`ndsrom.py`](../tools/ndsrom.py) from the image's
own structures, starting at offset 0.
[`reports/nds-header.txt`](../reports/nds-header.txt),
[`reports/nds-overlays.txt`](../reports/nds-overlays.txt),
[`reports/nds-banner.txt`](../reports/nds-banner.txt).

---

## The header

| Field | Value |
|---|---|
| game title | `TOIINNOCENCE` |
| game code | `AYTJ` |
| maker code | `AF` |
| unit code | `0x00` — Nintendo DS, not DSi |
| encryption seed | `0x00` |
| device capacity | `0x0A` = 134,217,728 bytes |
| region byte | `0x00` |
| ROM version | `0x00` |
| autostart | `0x00` |
| `ntr_rom_size` | 129,918,076 |
| header size | 16,384 |

The file is **134,217,728 bytes** and the capacity byte says 134,217,728, so
the dump is the whole cartridge and not a trimmed one. `J` in the fourth
position of the game code and region `0x00` are the Japanese release; there is
no other build here to compare, and the ROM version being 0 is consistent with
this being the first pressing but does not prove it.

**Nothing in this section comes from the dump's file name.** The name says
*Tales of Innocence (Japan)*; the header says `TOIINNOCENCE` / `AYTJ` / `AF`,
and the banner says `Tales of Innocence` and `バンダイナムコゲームス` in all
six language slots. Those agree. The developer is not in the header at all —
for that, see [09](09-leftovers.md).

### Modules and tables

| | ROM offset | size | RAM |
|---|---:|---:|---|
| ARM9 module | `0x00004000` | 676,952 | `0x02000000`, entry `0x02000800` |
| ARM7 module | `0x001FAA00` | 159,160 | `0x02380000`, entry `0x02380000` |
| ARM9 overlay table | `0x000A9600` | 96 | 3 entries |
| ARM7 overlay table | — | 0 | none |
| file name table | `0x00221800` | 105,414 | |
| file allocation table | `0x0023B400` | 51,024 | 6,378 entries |
| banner | `0x00247C00` | 2,560 | version `0x0001` |

The ARM9 autoload pointers are `0x02000AAC` and the ARM7's `0x02380188`; the
`ModuleParams` block sits at file offset `0xBA4` in `arm9.bin`, found by its
`0xDEC00621` / `0x2106C0DE` signature pair, and its SDK version word is
`0x04017531`.

### The three CRCs

| | declared | recomputed | |
|---|---|---|---|
| header CRC-16 | `0xFF17` | `0xFF17` | **OK** |
| Nintendo logo CRC-16 | `0xCF56` | `0xCF56` | **OK**, and equal to the retail constant |
| secure area CRC-16 | `0xC0C7` | `0xB068` | **does not match** |

The first two passing means the header and the boot logo are intact. The third
is discussed below and it is a property of the *dump*, not of the cartridge.

---

## The secure area

[`securearea.py`](../tools/securearea.py),
[`reports/secure-area.txt`](../reports/secure-area.txt).

The first 2 KiB of the ARM9 module — ROM `0x4000`–`0x4800` — ships encrypted on
a retail cartridge, with the ASCII marker `encryObj` at its head, and the
header's secure-area CRC-16 is computed over the encrypted form. A dump made
through a decrypting reader carries the plaintext, and the CRC therefore cannot
match. The measurement rather than the argument:

| restoration attempted | CRC-16 |
|---|---|
| as dumped | `0xB068` |
| `encryObj` written back over the first eight bytes | `0x3906` |
| eight zero bytes | `0x160E` |
| eight `0xFF` bytes | `0xCFD2` |
| **declared** | **`0xC0C7`** |

None of the four is the declared value, so the encrypted form cannot be
recovered from this image and the reading cannot be closed from this image
either. What the region *is* can be settled, and it is:

* entropy **7.893 bits** over the 2,048 bytes, 17 zero bytes, all 256 byte
  values present — which on its own reads as ciphertext or as generated filler;
* it contains **17 well-formed `svc #N ; bx lr` wrappers**, in ascending
  service order, and those are the NitroSDK's system-call thunks;
* the control: 1,980 windows of 2,048 bytes taken from `op.mods`, a
  4,055,640-byte video payload with entropy 7.548, contain **zero** such pairs.

Seventeen readable SDK thunks in one 2 KiB window, against none in four
megabytes of incompressible data, is code embedded in filler and not
ciphertext. The consequence for [05](05-block-codec.md) is that 2,048 bytes of
the ARM9 — 0.30% of it — are in a state the cartridge did not ship; the
constant scan covered them and found nothing at all, so nothing is hiding
there, but the caveat is real and it will be real on every DS image this corpus
opens. It was real on Tempest too, with different numbers.

---

## Where the 128 MiB went

[`formats.py`](../tools/formats.py), [`reports/budget.txt`](../reports/budget.txt).

| | bytes | share |
|---|---:|---:|
| header | 16,384 | 0.012% |
| ARM9 module | 676,952 | 0.504% |
| ARM7 module | 159,160 | 0.119% |
| file name table | 105,414 | 0.079% |
| file allocation table | 51,024 | 0.038% |
| banner | 2,560 | 0.002% |
| **files** | **125,906,775** | **93.808%** |
| slack between files | 2,999,807 | 2.235% |
| **unused tail** | **4,299,652** | **3.203%** |

The unused tail is **4,299,652 bytes and every one of them is `0xFF`** — no
zero-filled region, no boundary, one filler byte. *Tales of the Tempest* had
41.3% of its cartridge unused, split into 52,806,648 zero bytes followed by
exactly 2.5 MiB of `0xFF` on a power-of-two boundary, and this repository's
sibling could not say why. Here there is only the `0xFF`, and 96.8% of the
cartridge is in use.

The two facts are worth putting side by side, because they are the same fact
seen twice: Tempest had room to store everything raw and did; Innocence did not
have room, and compresses.

---

## The dates

[`datestamps.py`](../tools/datestamps.py),
[`reports/datestamps.txt`](../reports/datestamps.txt).

A DS cartridge has no volume descriptor and its FAT carries no timestamps, so
every date has to come out of a payload. There are no `__DATE__` / `__TIME__`
stamps in either executable — that shape returns zero hits over the whole
image. What there is:

| date | where | what it is |
|---|---|---|
| **2007-09-28 13:14:01–13:14:11** | overlay 1, nine strings | the CRI middleware build: `ADXT/NITRO Ver.10.36`, `NITROCI/NITRO Ver.1.02`, `NITRORNA/NITRO Ver.0.98`, `CRI CRW:STD/NITRO Ver.0.82`, `ADXNITRO Ver.1.00`, `MFCI/NITRO Ver.1.21`, `AHX/NITRO Ver.1.59`, `ADXCS/NITRO Ver.1.23` |
| **2007-10-07** | `arm9.bin+0xA4479` | the save-file signature, UTF-16: `TOIBACKUP:2007/10/07.0000021` |
| **2006-12-05, 16:56–18:34** | `/battle/list` | a Windows `dir` of `D:\toi\resorce\archive`, 265 files, 7,476,356 bytes, shipped in the game ([09](09-leftovers.md)) |
| **2005-01-31** | `/cutin/cutin_003.bin` | a `yymmdd` group in an asset name |
| **2006-02-12** | `/field/f040.bin` | the same shape |
| **2006-10-10** | `/cutin/cutin_006.bin` | the same shape |

Nine components stamped inside eleven seconds of each other is one library
build, not nine, so that is **one** independent date. Counting it once, four
independent sources land in a consistent order: assets from **January 2005**,
an archive directory from **December 2006**, a middleware build from
**28 September 2007**, and a save format frozen on **7 October 2007**.

Beside the neighbours:

| build | date the image states |
|---|---|
| *Tales of the Abyss*, PlayStation 2 | 2005-11-25 (volume descriptor) |
| *Tales of the Tempest*, Nintendo DS | 2006-09-21 19:19:58 (ARM9 build stamp), assets back to April 2005 |
| **Tales of Innocence, Nintendo DS** | **2007-09-28 (middleware), 2007-10-07 (save format)**, assets back to January 2005 |

The gap between the two DS cartridges is about a year in what the images state,
which matches their releases, and both reach back to early 2005 in their asset
names. Nothing here dates the *code*: Innocence, unlike Tempest, has no
compiler-written build stamp at all, and the two 2007 dates belong to a
middleware library and to a file format version.
