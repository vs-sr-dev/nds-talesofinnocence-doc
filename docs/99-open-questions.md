# 99 — Open questions

Each with the measurement that is actually in hand, so the size of the gap is
visible.

---

## The one that matters most: the format is the platform's and the code is not

**Open, and it is a contradiction rather than a gap.**

Established, three ways:

* **102 files are BIOS `LZ77` streams.** Each decodes and consumes its own
  file exactly, 16,901,069 bytes becoming 32,116,356, and 101 of them contain a
  structurally valid `EZBIND` archive afterwards. This is not a coincidence of
  first bytes.
* **The BIOS service is never called.** Twelve `svc #N ; bx lr` wrappers are
  linked across the two processors; **40,411 distinct branch targets** were
  resolved across all five modules, including across the module boundary from
  each overlay into the ARM9's wrapper table, and not one of the twelve has a
  caller — while `CpuSet` has one and `Stop/Sleep` seven. Ten words and thirty
  halfwords that match the `SVC` encoding without a following `bx lr` were all
  disassembled and every one is data. Each wrapper address, with and without the
  THUMB bit, was searched for as a 32-bit **data word** at every even offset in
  all five modules: **zero hits**, so it is not reached through a function
  pointer either.
* **The decompression must happen at run time.** `/field/f089.bin` and
  `/field/f091.bin` are shipped as plain uncompressed `EZBIND` while the other
  102 field archives are `LZ77`-wrapped, so the loader sniffs the first byte and
  handles both.

Not established: **where the decoder is.** [`lzprobe.py`](../tools/lzprobe.py)
looks for the format's own arithmetic — `(b0 >> 4) + 3` and
`(((b0 & 0x0F) << 8) | b1) + 1` — in five encoding families across all five
modules, in both instruction sets, and every co-location it returns was
disassembled and is a literal pool, a bone-name table read as instructions, a
touch-panel 12-bit mask, a script VM's flag masks, or the video decoder's
bitfield unpack. All eight literal-pool `4095` words in the ARM9 were traced to
their loaders and none is a ring mask.

Three readings survive and nothing here chooses between them:

1. the decoder is present and the probe's fingerprints are all wrong for how it
   was written — for instance a fully unrolled hand-written loop where the `+3`
   is three explicit stores and the nibble split is folded into an addressing
   mode;
2. it is reached in a way the branch resolver cannot see — a computed `bx` whose
   target is assembled arithmetically rather than loaded as a word;
3. something about the premise is wrong in a way three independent checks did
   not catch.

The probe is committed with its denominators so the next person can beat it.
**What this uncertainty does not touch** is [05](05-block-codec.md): the *Tales*
codec's constants are absent in both ARM encodings across 78,489 immediates,
140,305 THUMB literals and 554,020 words, and the reference decoder finds
nothing. The unlocated routine is a BIOS-format `LZ77` decoder, which is a
different algorithm with different constants.

## ~~Whether the corpus can now name the boundary~~

**Answered, by a different console, in the session after this one.**

Two Nintendo DS cartridges, two unrelated developers, one publisher, one year
apart, and neither carries the codec. That excludes the reading that Tempest's
zero was about *that team* in isolation, and it excludes the reading that the
*platform* forbids compression — this cartridge compresses 16.9 MB into 32.1 MB
in the platform's own format and fills 96.8% of the part.

What survived untouched was the third reading the corpus named: **both
developers are outside the Namco Tales Studio line**, and a codec that travelled
with a codebase would not be expected to reach either. This document asked for a
Nintendo title *from* that line and said there was not one.

**There is one, and it is not on this machine.** *Tales of Symphonia: Ratatosk
no Kishi* (Wii, 26 June 2008) is the direct sequel to the 2003 GameCube
*Tales of Symphonia* — the corpus's only PowerPC positive, which carries the
decoder four times and decodes 487 of 487 blocks. Same studio line, same
processor family, a Nintendo console, five years later. It does not carry the
codec: zero `4078` / `4079` / `4070` / `4071` over 637,871 PowerPC instruction
words, zero fingerprint clusters where the 2003 build has four, and zero blocks
across its 4.29 GB game partition under the same unmodified reference decoder
that returns 1,089 on the 1995 cartridge.

And because both builds are Metrowerks PowerPC `.dol` files, the strong byte
test ran for the first time across a console generation: 872 bytes of the 2003
decoder score **10 bytes** in the 2008 executable — the same as an unrelated
Wii title — while the two executables share **835 contiguous identical bytes**
of Nintendo SDK code that no control image has.

So the alternative this document could not exclude is excluded. *"The codebase
never shipped a Nintendo title"* is false: it shipped two, and the first one
carries the codec. **The two zeros on this machine are facts about the two DS
developers, not about the reach of the codebase** — and what remains open
is not a platform question at all but a date: the codec's last confirmed
appearance is *Tales of the Abyss*, 25 November 2005, and its first confirmed
absence from the line is June 2008.
[wii-talesofsymphoniadotnw-doc](https://github.com/vs-sr-dev/wii-talesofsymphoniadotnw-doc)

## The `EZBIND` tag at `+0x0C`

**Open.** Distinct within an archive on 1,343 of 1,344 archives, and not the
member's size, offset or index. Members whose names differ only in their last
character get tags that differ only in their low byte —
`logoalfa.nbfc` / `.nbfp` / `.nbfs` give `0x396F7638`, `0x396F7645`,
`0x396F7648` — which reads like a name hash, but the low-byte differences do not
match the character differences and no function tried here reproduces the value.
It is reported as a tag.

One archive, `/battle/btleff.bin`, has the tag repeated between two members
while tiling correctly in every other respect. If the tag is the lookup key,
that archive has a collision in it, and nothing here says whether that mattered.

## The secure area

**Consistent, and it will be on every DS image this corpus opens.** The header
declares CRC-16 `0xC0C7`; the region as dumped computes `0xB068`, and
restoring `encryObj`, eight zeros or eight `0xFF` over the first eight bytes
gives `0x3906`, `0x160E` and `0xCFD2`. None is the declared value, so the
encrypted form cannot be recovered from this image.

What the region *is* can be settled: entropy 7.893 bits over 2,048 bytes, and
**17 well-formed `svc #N ; bx lr` wrappers** inside it, against **zero** in
1,980 control windows of 2,048 incompressible bytes taken from the video file.
That is SDK code in generated filler, not ciphertext. 2,048 bytes of the ARM9 —
0.30% — are therefore in a state the cartridge did not ship; the constant scan
covered them and found nothing at all. [02](02-cartridge-and-header.md).

## The Mobiclip header

**Partly open, and no duration is quoted because of it.** Four fields of
`/test/op.mods` are read and cross-checked: frame count 2,136, frame size
256 × 192 (the DS screen), audio rate 32,000 Hz, and the magic `MODS` with a
`N2\n\0` tag at `+0x04`. Unread: `+0x14` (`0x17F9DCB5`), `+0x18`
(`0x00020002`), `+0x20` (24,348), `+0x28` (4,055,184, which is 456 short of the
file size), `+0x2C` (57) and `+0x30`.

**No frame-rate field is identified**, so no duration is stated anywhere in this
repository. That is the same decision *Tales of the Tempest* made about the
`+0x04` count in its Actimagine `VXDS` headers, and for the same reason: a
number derived from a guess is worth less than no number.

## Why the world map is named after a test scene

**Open.** 196 of the 200 files in `/world` are `f_test04_Room_00` …
`f_test04_Room_79`, 2,720,448 bytes, each an `EZBIND` holding a model, a texture
animation, a collision pair and a bounding box. The four that are not are
`WorldMap.dat`, `WorldArea.dat`, `world2d.bin` and `worldtex.bin`. Either a test
scene became the shipping world-map content and kept its name, or the shipping
content never displaced it. The image does not say which, and the models are not
placeholders — they carry real internal names (`base_bridge`, and the whole
`f_test04_Room_NN.nsbmd` family appears in the internal-name harvest).

## The AHX sample rate

**Open, and it changes a number.** All 2,356 AHX voice files declare a sample
rate of **16,364 Hz** and all 87 mono ADX declare the same; the one stereo ADX
declares 32,728, exactly twice. Those are odd rates. The 2.72-hour AHX figure in
[07](07-media-and-budget.md) is `samples / rate` from the header, and for AHX the
encoder's true rate lives inside the MPEG frames rather than in the CRI header,
so the figure is the header's arithmetic and not a measured duration. The frames
were not parsed. If the declared rate is nominal, the total is wrong by whatever
factor separates them.

## `cTolWorldShip`

**Open, and small.** One class name in 1,047 reads `Tol` where its sixty
neighbours read `Toi`, and `ToL` is *Tales of Legendia*'s project tag. There is
no other `Tol` on the cartridge, and no Legendia asset, tag, format or name for
it to belong to. A typing slip is by far the likeliest explanation and it is not
provable from the image. [08](08-cross-title.md).

## Why the unused tail is all `0xFF`

**Open, and it is the same question Tempest left, with the other answer.**
4,299,652 bytes of tail, every one `0xFF`, no zero region and no boundary.
Tempest's tail was 52,806,648 zero bytes followed by exactly 2,621,440 `0xFF`
with the boundary on a power-of-two address, and that repository could not say
why there were two fillers. This one has one. Two cartridges from two studios
through what may or may not be the same mastering tool, and the images do not
say.

## The in-house formats that were not taken apart

**Open, and counted rather than read.**

* **`.dat` collision and attribute data**, 1,269 members, 2,273,600 bytes,
  3.76% of the container bytes. Always paired as `*_attr.dat` and
  `*_attr_area.dat` beside a model.
* **`.imb` / `.mpb` / `.plb`**, 39 of each, 1,877,882 bytes together, all inside
  `/staff/ed01.bin` … `ed13.bin` — the ending image sequence. The sizes are
  round (65,152 and 65,536 for the `.imb`, 4,096 and 2,048 for the `.mpb`, 510
  for the `.plb`), which reads as bitmap / map / palette, but no layout equation
  was tested against them.
* **`.boxtest`**, 1,733 members, sixteen bytes each — a bounding box, and
  sixteen bytes is two `s16` triples plus padding or four `s32`; nothing here
  chooses.
* **`.layout`** (71), **`.ep`** (30), **`.pix`** (17), and the top-level
  `.scr` scripts (783) and `.fdt` face data (76), which announce themselves with
  `FaceChat` and `FaceData` magics and are otherwise unread.

The budget counts every one of these bytes; it does not claim to understand
them.

## Whether "4,591 unmentioned file names" means anything

**It does not mean deadness, and the tool says so.** 4,591 of 6,378 file names
are not spelled out anywhere in the image outside the file name table,
accounting for 87,415,064 bytes — but the ARM9 carries `facechat/ev%04d.scr`,
`battle/%s_mdl.bin`, `chara%02d.nbfc`, `Weapon%03d.nbfc` and a dozen more format
strings, so most of the cartridge is addressed by a name built at run time. The
number is a real measurement of *how the loader works*; it is not a count of
unused files, and no file on this cartridge is claimed to be unreferenced.
