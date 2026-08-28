# 05 — The block codec

The measurement this repository exists for. The format is specified in
[tales-blockcodec-doc](https://github.com/vs-sr-dev/tales-blockcodec-doc); this
document says whether it is on this cartridge, with every denominator printed.

**It is not.** And this time the zero is clean enough that it says something the
previous Nintendo DS zero could not.

[`ring_sites.py`](../tools/ring_sites.py),
[`struct_probe.py`](../tools/struct_probe.py),
[`nearmiss.py`](../tools/nearmiss.py),
[`blind_decode.py`](../tools/blind_decode.py),
[`tales_block.py`](../tools/tales_block.py).

---

## Step 0 — decompress the modules first

Done, three ways, before anything was scanned. Nothing is compressed:
`compressed_static_end = 0`, all three overlay flags clear, all five `BLZ`
footers reporting a zero length delta. [04](04-executables.md).

This matters because a scan of a packed module returns zero and is
indistinguishable from a real negative. Two DS cartridges in, that trap has
still not been sprung, and the only reason we know is that the check was run.

---

## Step 1 and 2 — the constant, in both of ARM's two encodings

An ARM data-processing immediate is an 8-bit value rotated right by an even
amount. Nine significant bits do not fit, so:

| constant | ARM immediate? |
|---|---|
| 4070 (`0xFE6`) | **no** — literal-pool word |
| 4071 (`0xFE7`) | **no** — literal-pool word |
| **4078 (`0xFEE`)** | **no** — literal-pool word |
| **4079 (`0xFEF`)** | **no** — literal-pool word |
| 4080 (`0xFF0`) | **yes**, `0xFF ror #28` |

In THUMB `mov rd, #imm8` reaches 255, so all five are pool words there too. Both
passes were run on all five modules, and both denominators are printed.

| | ARM9 | ARM7 | ovl 0 | ovl 1 | ovl 2 | **total** |
|---|---:|---:|---:|---:|---:|---:|
| ARM data-processing immediates | 22,568 | 11,882 | 22,350 | 18,419 | 3,270 | **78,489** |
| THUMB instructions carrying a literal | 43,310 | 5,253 | 56,540 | 30,972 | 4,230 | **140,305** |
| 4-byte-aligned words | 169,238 | 39,790 | 178,200 | 144,328 | 22,464 | **554,020** |
| PC-relative loads resolved | 10,268 | 2,293 | 6,247 | 8,037 | 624 | **27,469** |
| distinct load targets | 7,624 | 1,796 | 5,744 | 6,586 | 512 | **22,262** |
| **4078 / 4079 / 4070 / 4071 / 4080, either form** | **0** | **0** | **0** | **0** | **0** | **0** |

[`reports/ring-sites-arm9-arm7.txt`](../reports/ring-sites-arm9-arm7.txt),
[`reports/ring-sites-overlays.txt`](../reports/ring-sites-overlays.txt).

This is a stronger zero than Tempest's. That cartridge had five `4080`
immediates and one unreferenced `4080` word to account for — four of them
entries of a 4,096-scaled cosine table, because `round(4096 · cos 5°) = 4080`.
Here **not one of the five constants occurs anywhere, in either encoding, in
any of the five modules**. There is nothing to explain away.

---

## Step 3 — the structures, which a compiler cannot rewrite away

[`struct_probe.py`](../tools/struct_probe.py),
[`reports/struct-probe.txt`](../reports/struct-probe.txt).

The constant can in principle be computed rather than loaded, so the shapes are
counted too, in the encodings ARM actually has for them.

| fingerprint | ARM9 | ARM7 | ovl 0 | ovl 1 | ovl 2 |
|---|---:|---:|---:|---:|---:|
| `orr rX, rX, #0xFF00` — the control refill, **encodable on ARM** | **0** | **0** | **0** | **0** | **0** |
| immediates equal to `0xFF00` at all (`and`, `cmp`, `add`) | 5 | 28 | 0 | 38 | 0 |
| `and #4095` — not encodable, so: literal-pool 4095 | 8 | 4 | 15 | 9 | 0 |
| …`lsl #20` + `lsr #20` pairs, ARM / THUMB | 0 / 3 | 0 / 0 | 0 / 1 | 0 / 0 | 0 / 0 |
| immediates equal to 4096 | 90 | 31 | 43 | 33 | 5 |
| **`add`/`sub` on `sp` with a 4096-byte frame** | **0** | **0** | **0** | **0** | **0** |
| ARM `add #19` | 1 | 0 | 0 | 0 | 0 |
| sites where three of the five land within 200 instructions | 0 | 0 | 0 | 0 | **10** |

Two of these need reading rather than tabulating, and both were read.

**The `0xFF00` immediates are not refills.** The control register of this codec
is refilled as `flags = byte | 0xFF00`, and on ARM that is `orr rX, rX, #0xFF00`
— encodable, so a probe finds it. There are **zero** `orr` forms across all five
modules. The 71 immediates that do equal `0xFF00` are `and`, `cmp` and one
`add`: masks and comparisons, not a refill.

**Overlay 2's ten sites are the ARM/THUMB trap, plus one bitfield unpack.**
This is the specific failure section 7 warns about, and it fired exactly as
described. `nearmiss.py` prints, for every THUMB hit at an even-but-not-word
offset, the ARM word that contains it:

```
THUMB 0x0212F8A0  add r6,#19 -- containing ARM word 0xE1A03613  mov r3,r3,lsl r6
THUMB 0x02130AA8  add r6,#19 -- containing ARM word 0xE1A03613  mov r3,r3,lsl r6
THUMB 0x021334D4  add r5,#19 -- containing ARM word 0xE1B03513  movs r3,r3,lsl r5
   ... 22 in all, every one of them an ARM word read at an even offset
```

Overlay 2 is ARM code, and `mov r3,r3,lsl rN` — the bit-consume step of a
Huffman decoder, repeated all through it — reads as `add rN,#19` when its second
halfword is decoded as THUMB. The genuine ARM `add #19` count in overlay 2 is
**zero**, exactly as it was on Tempest, where 24 identical false positives came
out of the same idiom.

The three remaining sites are real ARM code and they are innocent:

```
021334C0  E204500F   and     r5,r4,#15
021334C4  E1A04224   mov     r4,r4,lsr #4
021334C8  E204601F   and     r6,r4,#31
021334D0  E1A042A4   mov     r4,r4,lsr #5
021334E4  E204503F   and     r5,r4,#63
```

A halfword pulled from a twelve-bit lookup table and unpacked into 4-, 5-, 5-
and 6-bit fields. That is the Mobiclip decoder's symbol table, not a
nibble-pair token; the token this codec uses splits a byte into two nibbles and
adds three, and there is no `+3` within reach of any of the three.
[`reports/near-misses.txt`](../reports/near-misses.txt).

The ARM9's single genuine ARM `add #19` is `addeq r2,r0,#19` at `0x02069AE4`,
conditional, with no nibble split, no mask and no refill anywhere near it.

---

## Step 4 — the reference decoder, run blind

[`blind_decode.py`](../tools/blind_decode.py),
[`reports/blind-decode.txt`](../reports/blind-decode.txt).

`tales_block.py` is the corpus's own decoder, copied from
[tales-blockcodec-doc](https://github.com/vs-sr-dev/tales-blockcodec-doc)
unmodified — md5 `e2dcd6b8dc717b84f67bf8a46568298c` — and not reimplemented, so
a negative here means the same decoder that reads all ten positive builds also
read these bytes and found nothing. It was offered, **in both dialects**:

* the cartridge image, swept by its gaps rather than as one buffer;
* `arm9.bin` and `arm7.bin`;
* every one of the 6,378 FAT files;
* every one of the 9,646 `EZBIND` members, including the members of the 101
  archives that had to be decompressed first;
* every BIOS-format stream decompressed and offered again;
* every `SDAT` sub-file and every Nitro `BMD0`/`BTX0` block.

**Per payload, never as one buffer.** Section 7 is explicit about why and the
reason is arithmetic: `plausible()` bounds a candidate by whether its declared
stream fits in the buffer it sits in, which inside a 64 KB file rejects nearly
everything for free and inside 134 MB rejects almost nothing. Swept as one
buffer this cartridge does not finish.

**23,083 payloads, 657,419,133 bytes, both dialects, zero blocks.**

The control is run in the same invocation and on the same decoder: the 1995
Super Famicom cartridge, which returns its **1,089** blocks, and the two loops
inside the tool — `tales_block.scan` and the sweep this file uses instead —
agree on that figure. A negative is only worth quoting if the instrument is
shown to work in the same breath.

Beside *Tales of the Tempest*, which had no container to descend into: 9,055
payloads and 256,548,562 bytes. The byte count here is 2.6 times larger than
this cartridge is, because every compressed archive is offered twice — once as
it is stored and once decompressed — and then again member by member.

`tales_block.py --selftest` also passes here
([`reports/selftest.txt`](../reports/selftest.txt)) — the `+3` and `+19` run
bases agree across both dialects over the whole 4–18 and 19–274 range — so the
decoder that returned zero is the specified one.

---

## What this contributes to section 6

The corpus's eleventh build could not separate two variables. Its own words:

> *Tales of the Tempest* changes **the machine and the team together**, so its
> zero is compatible with the boundary being either one. The corpus needs a
> Nintendo DS control — a title from the same publisher and a different
> developer, or from the same developer and a different series — before this
> build can narrow anything.

This is that control, in the first of those two forms: same publisher, same
platform, one year later, a **third** studio outside the Namco Tales Studio
line. And it returns the same zero on the codec.

That resolves less than it looks like and more than nothing, and the
distinction is the whole point:

**What it does settle.** Two Nintendo DS cartridges, two unrelated developers,
one publisher, and neither carries the codec. A single-team explanation for
Tempest's zero now requires the same accident twice.

**What it does not settle.** Both developers are outside the studio line that
carried the codec from 1995 to 2005. The third reading the corpus named — *both
teams are external, and that is the whole story* — survives this cartridge
untouched, and it would take a DS title **from** that line to attack it. There
is no such thing.

**What it removes.** The reading that the *platform* forbids it. That one is
gone, and it is gone by measurement rather than by argument. Tempest's zero came
with no compression of any kind on the cartridge, no BIOS call, and 41.3% of the
medium unused; it was possible to read that as "the DS pipeline did not
compress". Innocence compresses **16,901,069 bytes into 32,116,356** in the
platform's own `LZ77` format, wraps 60 MB in a container of its own, licenses
two middleware stacks, and leaves 3.2% of the cartridge spare. This is a DS
*Tales* cartridge with a full compression pipeline in it, and the pipeline is
not this one.

So the row this build contributes to section 6 reads **"no — and the platform
is now excluded as the explanation"**, and the sentence Tempest could not
finish becomes: the boundary is not the machine.
