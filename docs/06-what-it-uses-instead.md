# 06 — What it uses instead

Section 7 of the codec specification says that for a non-console target the
first question is what the platform already gives you, because that is what a
small team will use. On the 2003 Game Boy Advance rebuild of *Phantasia* the
answer was the BIOS `LZ77UnComp` and `RLUnComp`. On *Tales of the Tempest* the
answer was **nothing at all** — six services offered free, twelve wrappers
linked, none called, and the data stored raw.

This cartridge answers it a third way, and the answer is in two halves that
disagree with each other.

---

## Half one: the data is in the BIOS formats

[`ndscomp.py`](../tools/ndscomp.py),
[`reports/bios-compression-census.txt`](../reports/bios-compression-census.txt),
[`reports/bios-stream-sweep.txt`](../reports/bios-stream-sweep.txt).

**106 of 6,378 files begin with a BIOS-format stream that decodes and consumes
the whole file:**

| format | files | packed | unpacked | ratio |
|---|---:|---:|---:|---:|
| `LZ77` (`0x10`) | **102** | 16,901,069 | 32,116,356 | **1.90×** |
| `RLE` (`0x30`) | 1 | 6,657 | 6,736 | 1.01× |
| Huffman 4-bit (`0x24`) | 1 | 6,108 | 6,736 | 1.10× |
| Huffman 8-bit (`0x28`) | 1 | 3,296 | 3,376 | 1.02× |
| difference filter 16-bit (`0x82`) | 1 | 6,740 | 6,736 | 1.00× |
| **total** | **106** | **16,923,870** | **32,139,940** | **1.90×** |

The 102 `LZ77` files are 101 of the 104 field archives plus one of the five test
files below. Against Tempest's **zero of 4,712**, and against its 91,303
candidate offsets yielding zero embedded streams, this is a different cartridge
entirely.

The embedded sweep agrees and adds nothing: over all 6,378 files at step 4,
**194,310 offsets carried a type byte and a plausible size, 131 survived a
256-byte trial decode, and 102 decoded in full and actually compressed
something** — and all 102 are at offset 0 of their own file. There are no
streams buried inside other payloads.

**The caveat the previous cartridge imposed still applies and is still stated.**
Of the seven BIOS formats only `LZ77` can be *excluded* by decoding, because it
rejects a back-reference before the start of the output and its geometry caps
the ratio at 18 / 2.125 = 8.47×. `RLE` and the two difference filters accept any
byte sequence, a small Huffman tree walks arbitrary bits happily, and `LZ11`'s
four-byte token reaches 65,808 output bytes with no ratio bound. So `LZ77` is
swept and the rest are reported by header count with the reason. The header
count, for comparison with the table above:

| type byte | files whose first four bytes have that shape |
|---|---:|
| `0x10` `LZ77` | 103 |
| `0x11` `LZ11` | 2 |
| `0x24` Huffman4 | 1 |
| `0x28` Huffman8 | 1 |
| `0x30` `RLE` | 1 |
| `0x82` Diff16 | 1 |

The one `LZ77`-shaped file that does not decode is `/field/e022t000.dat`, 232
bytes, and it is a 232-byte data file whose first byte happens to be `0x10`. The
two `LZ11`-shaped ones are `/field/e115t000.dat` (24 bytes) and
`/navi/navimap_66.nbfc` (15,360 bytes), and the permissive-format caveat is
exactly why neither is claimed.

### The corpus's first positive control for these decoders

[`reports/bios-format-control.txt`](../reports/bios-format-control.txt).

`/motion/alb000/` contains something nobody in this corpus has had before: **the
same animation shipped five times over, once per format, next to the original.**

```
00_HUFF.bin     3296  0x28 Huffman8  ->    3376  consumed 3296/3296  identical to 00.nsbca: YES
01_LZ.bin       6174  0x10 LZ77      ->    6736  consumed 6174/6174  identical to 01.nsbca: YES
01_RL.bin       6657  0x30 RLE       ->    6736  consumed 6657/6657  identical to 01.nsbca: YES
01_HUFF.bin     6108  0x24 Huffman4  ->    6736  consumed 6108/6108  identical to 01.nsbca: YES
01_DIFF.bin     6740  0x82 Diff16    ->    6736  consumed 6740/6740  identical to 01.nsbca: YES
```

Somebody ran a compression benchmark on one 6,736-byte animation, kept all five
outputs and the input, and shipped the lot. The winner is `LZ77` at 6,174 bytes
and the loser is the difference filter, which is not a compressor and produced
four bytes more than it was given.

**It found two defects in `ndscomp.py`**, and both had been silently wrong since
the tool was written for a cartridge that contained no such stream to catch
them:

1. **The difference filters were one type byte low.** The DS's filter type byte
   is `0x80 | width_code` with the width code 1 for 8-bit and 2 for 16-bit, so
   the two filters are `0x81` and `0x82` — not `0x80` and `0x81`, and `0x80` is
   not a stream type at all. The consequence was not cosmetic: **2,444 CRI audio
   files begin `0x80 0x00`**, so a census over this cartridge reported 2,444
   "Diff8" files that were nothing of the kind, and a census over Tempest
   reported its own `0x80` count under the wrong name.
2. **The Huffman decoder was broken in two places at once.** Its leaf mask
   tested `0x40 >> bit` where the ABI puts the zero-child flag in bit 7 and the
   one-child flag in bit 6, so the correct mask is `0x80 >> bit`; and it
   computed the child index relative to the tree array rather than from the
   node's own address, which loses the `& ~1` alignment — and the tree always
   starts at an odd address, because the tree-size byte sits in front of it.
   Both failures surface as `tree overrun` or `input exhausted`, which read
   exactly like a file that is not Huffman.

Both are fixed and both are checked, in the committed tool, against these five
files. `magic_sweep.py`'s type table was corrected to match.

---

## Half two: the BIOS is never called

[`bios_calls.py`](../tools/bios_calls.py),
[`reports/bios-calls.txt`](../reports/bios-calls.txt).

The NitroSDK links a table of `svc #N ; bx lr` wrappers into every build,
decompression services included, whether or not anything uses them. Presence
therefore says only that the library was linked, and the question is whether
anything branches to one. So every branch in every module was resolved and
counted against every wrapper.

| | ARM9 (+ its three overlays) | ARM7 |
|---|---:|---:|
| decompression wrappers linked | 6 | 6 |
| distinct branch targets resolved | **36,628** | **3,783** |
| **call sites, all six decompression wrappers** | **0** | **0** |
| `CpuSet` | 1 | 0 |
| `Stop/Sleep` | 7 | 0 |

**40,411 distinct branch targets, twelve decompression wrappers, zero callers**
— while `CpuSet` has one caller and `Stop/Sleep` seven, so the instrument is
shown to find callers where there are callers.

**This measurement had to be extended for this cartridge, and the extension is
itself a result.** Tempest had no overlays, so resolving branches within one
image was the whole search. Here the wrappers are linked once, into `arm9.bin`,
and an overlay that wanted one would branch to it *across* the module boundary —
a call site the single-image form cannot see, because an overlay links no
wrapper of its own and therefore has nothing to count against. `bios_calls.py`
gained an `--also FILE@VA` option so that one wrapper table is counted against
four images' branches at once. The answer does not change; the measurement is
now the right one.

Two further checks, because "no branch" is not "no call":

* **No inline `svc`.** Ten words and halfwords in the ARM9 and thirty more
  across the overlays match the SVC encoding without being followed by `bx lr`.
  All were disassembled. Every one is data — pointer tables of THUMB addresses
  such as `0x0204DEC5`, `0x0204DF11`, `0x0204DF1D`, whose low bytes decode as
  `svc #0xC5`, `#0x11`, `#0x1D` when read as THUMB. There is no `svc #0x11` that
  is an instruction anywhere on this cartridge.
* **No function pointer.** Each of the twelve wrapper addresses, with and
  without the THUMB bit, was searched for as a 32-bit **data word** at every
  even offset in all five modules. **Zero hits.** An indirect call would have to
  leave the address somewhere, and it does not.

---

## The contradiction, stated as a contradiction

The data is in the DS BIOS's `LZ77` format. The DS BIOS's `LZ77` service is
never called. **Where the decoder is, is not established.**

Somebody has to read those 102 files, and two of the 104 field archives —
`f089.bin` and `f091.bin`, both 152,720 bytes and byte-identical to each other —
are shipped as **plain uncompressed `EZBIND`**, so the loader must sniff the
first byte and handle both. That is a runtime decision, not a build artefact.

[`lzprobe.py`](../tools/lzprobe.py) exists to look for it and returns nothing.
It counts the format's own arithmetic — `length = (b0 >> 4) + 3` and
`displacement = (((b0 & 0x0F) << 8) | b1) + 1` — in every encoding a compiler
would plausibly choose, in both instruction sets, across all five modules:

| fingerprint | co-locations within 40 instructions, all five modules |
|---|---:|
| ARM `mov rD,rS,lsr #4` near an `add #3` | **0** |
| ARM `and #15` near an `orr`/`add ..., lsl #8` | 5 |
| THUMB `lsr #4` near an `add #3` (both imm3 and imm8 forms) | 25 |
| THUMB `mov #15` or `lsl #28`/`lsr #28` near a `lsl #8` | 225, none with a `+3` in reach |
| the halfword-token variant: ARM `lsr #12` near an `add #3` | 1 |
| the halfword-token variant: THUMB `lsr #12` near an `add #3` | 13 |
| the do/while variant: `lsr #4` near a `+2` or `+1` | counted and read, all innocent |

Every co-location was disassembled and none of them is a decoder.

The five ARM `and #15` sites split three ways. Two, at `0x02068B94` and
`0x02068BB8` in the ARM9, are **THUMB instructions read as ARM words** — the
trap of [05](05-block-codec.md) running in the opposite direction: the word
`0x0200200F` is `and r2,r0,#15` as ARM and `lsl r0,r0,#8 ; mov r0,#15` as the
THUMB pair it actually is, in the middle of a THUMB routine. Two more, in
overlay 2 at `0x021334C0` and `0x0213350C`, are the video decoder's 4/5/6-bit
symbol unpack. The last is real ARM and is a hardware handshake on the ARM7:

```
023864F8  E1A00405   mov     r0,r5,lsl #8     ; a 4-bit command in the high byte
023864FC  E1C800B0   strh    r0,[r8]
02386504  EBFFFE83   bl      0x02385F18       ; delay
02386508  E1D800B0   ldrh    r0,[r8]
0238650C  E200000F   and     r0,r0,#15        ; read the 4 bits back
02386510  E1500005   cmp     r0,r5            ; and check they arrived
```

The other families are the same kind of thing: literal pools (`0x0210090C`,
`0x0210E4F0` — words between routines, which is why the byte after a `lsr #4`
happens to be an `add #3`), 3ds Max bone-name tables read as instructions, a
touch-panel coordinate mask (`lsl #20`/`lsr #20` on a 12-bit value), a script
VM's flag masks, and a 12/20-bit field pack in the ARM9's 3D code. Separately,
all eight literal-pool `4095` words in the ARM9 were traced to the instructions
that load them: three are script-VM `tst` masks, one is a struct initialiser,
one is not loaded at all.

So the honest statement is the one in [99](99-open-questions.md): **the format
is the platform's and the code is not the platform's, and the code was not
found.** The probe is the limitation, not the evidence — and the probe is
committed, with its denominators, so the next person can beat it.

---

## What else is here instead

### CRI Middleware

Nine components, all stamped inside eleven seconds of one build,
**2007-09-28 13:14:01–13:14:11**, in overlay 1:

```
ADXT/NITRO Ver.10.36        NITROCI/NITRO Ver.1.02
NITRORNA/NITRO Ver.0.98     CRI CRW:STD/NITRO Ver.0.82
ADXNITRO Ver.1.00           MFCI/NITRO Ver.1.21
AHX/NITRO Ver.1.59          ADXCS/NITRO Ver.1.23
```

with `Append: MW4020` beside them. What they run is 2,444 audio streams: 2,356
**AHX** (MPEG-2 layer II) and 88 **ADX** (CRI's ADPCM), 56,208,162 bytes,
identified from the `(c)CRI` marker in each header rather than from the
extension. [07](07-media-and-budget.md).

The library also links CRI's `ROFS` volume reader — three `ROFS` strings sit in
a format-name table beside `RIFF` and `criSsPly_Play` — but no `ROFS` volume is
on the cartridge.

### Actimagine

`[SDK+Actimagine:MO]` in the ARM9's component list, against Tempest's
`[SDK+Actimagine:VX]`. `MO` is **Mobiclip**, and the single video file is
`/test/op.mods`, 4,055,640 bytes, magic `MODS`, 2,136 frames at 256 × 192 with
32,000 Hz audio. The decoder is overlay 2: ARM, heavily unrolled, driven by a
twelve-bit peek into a lookup table of halfwords that carry a 4-bit code length
and 5- and 6-bit symbol fields, with a bit-count underflow branching to a refill
routine. It is the routine whose `mov r3,r3,lsl rN` idiom produces all 22 of the
false `add #19` fingerprints in [05](05-block-codec.md).

### Nintendo

`SDAT`, one archive, 8,732,192 bytes: 49 `SSEQ` sequences, 69 `SBNK` banks, 68
`SWAR` wave archives, 20 `SSAR` and 310 `STRM` streams, with a full `SYMB` block
naming every one of them. The music is sequenced; the DS sound hardware's own
IMA-ADPCM does the streams. [07](07-media-and-budget.md).

### And the control that depends on nothing

[`deflate_control.py`](../tools/deflate_control.py),
[`reports/deflate-control.txt`](../reports/deflate-control.txt).

Every byte through `zlib` at level 9. This depends on no fingerprint at all.

| | bytes | deflates to |
|---|---:|---:|
| the whole cartridge | 134,217,728 | **73.47%** |
| audio | 64,940,354 | 90.43% |
| video | 4,055,640 | **99.24%** |
| containers **already inside a BIOS stream** | 16,894,895 | **91.27%** |
| containers **not** compressed | 28,682,996 | **52.23%** |
| 3D animation | 6,819,832 | 79.09% |
| 2D graphics | 1,652,302 | **5.43%** |
| `arm9.bin` | 676,952 | 55.44% |

*Tales of the Tempest* deflated to **52.6%** as a whole, its palettes to 9.3%
and its bitmaps to 16.1% — three numbers that agreed with a zero branch count
and a zero header census and made "the data is stored raw" safe to say.

Here the same tool says the opposite in the same words. The cartridge as a whole
gives back only 26.5%, because half of it is MPEG audio and Mobiclip video that
are already packed. The one row that settles the argument is the split inside
the containers: the 101 archives that arrive in an `LZ77` stream deflate to
**91.27%** — there is nothing left in them — and the 1,245 that do not deflate
to **52.23%**. The compressor was applied to some of the data and not to the
rest, and deflate can see exactly which.
