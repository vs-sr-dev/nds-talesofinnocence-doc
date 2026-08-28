# tools

Python 3, standard library only, one file per job, no dependencies. On Windows
set `PYTHONIOENCODING=utf-8` — several of these print Shift-JIS.

Eleven of these came from
[nds-talesofthetempest-doc](https://github.com/vs-sr-dev/nds-talesofthetempest-doc),
which is the reusable half of any Nintendo DS pipeline. Five of the eleven had
to be **extended** for this cartridge, and each extension is a result in its own
right, because it names something Tempest did not have. The extensions are
listed below and are documented in the tools themselves.

`tales_block.py` is copied from
[tales-blockcodec-doc](https://github.com/vs-sr-dev/tales-blockcodec-doc)
unmodified — md5 **`e2dcd6b8dc717b84f67bf8a46568298c`** — so that a negative
means the same decoder that reads all ten positive builds also read these bytes.

---

## The cartridge

| tool | what it does |
|---|---|
| **`ndsrom.py`** | header, three CRCs, FNT, FAT, both overlay tables, banner, `--extract` |
| **`securearea.py`** | what is really in the 2 KiB secure area: the declared CRC against three restorations, entropy, the SDK wrappers inside it, and the same count over N control windows |
| **`datestamps.py`** | **new.** every date the image states about itself — `__DATE__`/`__TIME__` shape, ISO dates, middleware build strings, and `yyyymmdd` / `yymmdd` groups in names — each located in the file system |

## Compression, the platform's and the game's

| tool | what it does |
|---|---|
| **`ndscomp.py`** | `LZ77`, `LZ11`, both Huffmans, `RLE`, both difference filters, plus `BLZ`. `--blz` runs *before* any scan, because a scan of a compressed module returns a clean-looking zero |
| **`ezbind.py`** | **new.** the in-house `EZBIND` container: layout, a four-claim structural check run on every archive, `--census`, `--walk` (descending through compression and nesting), `--extract` |
| **`deflate_control.py`** | **new.** every byte through `zlib`, by the budget's own classes. Depends on no fingerprint at all, which is what makes it a control |

`ndscomp.py` was extended three ways here:

* `--census` and `--sweep` **walk the tree**. They used `os.listdir`, which was
  right for a cartridge whose file system was one flat directory and measures
  *zero files* on one with 156 of them — reporting it in the same words a real
  negative uses.
* the **difference-filter type bytes** were one place low. The DS header is
  `0x80 | width_code` with 1 for 8-bit and 2 for 16-bit, so the filters are
  `0x81` and `0x82` and `0x80` is not a type at all. It mattered: 2,444 CRI
  audio files begin `0x80 0x00`.
* the **Huffman decoder** was wrong in two places — the leaf mask was
  `0x40 >> bit` where the ABI puts the flags in bits 7 and 6, and the child
  address was computed from a tree-relative index, which loses the `& ~1`
  alignment on a tree that always starts at an odd address. Both surface as
  `tree overrun`, which reads exactly like a file that is not Huffman.
* `--verify FILE REF` was added, because this cartridge supplies the corpus's
  first **positive control** for all five formats
  ([`reports/bios-format-control.txt`](../reports/bios-format-control.txt)).

`magic_sweep.py`'s type table was corrected to match.

## Code

| tool | what it does |
|---|---|
| **`disarm.py`** | a small ARMv5TE / THUMB disassembler, enough to read a routine |
| **`bios_calls.py`** | every `SWI`, filtered to the two forms that are certainly instructions, then **every branch resolved and counted against each wrapper** |
| **`symbols.py`** | **new.** the C++ `type_info` names RTTI left in the images — length-prefixed, so the scan is exact — grouped by leading identifier |
| **`lzprobe.py`** | **new.** is the platform's `LZ77` *format* decoded by code in this image? Five fingerprint families, both instruction sets, all denominators printed |

`bios_calls.py` gained **`--also FILE@VA`**, which resolves a further image's
branches against the *same* wrapper table. Tempest had no overlays, so
resolving within one image was the whole search; here the wrappers are linked
once into `arm9.bin` and an overlay that wanted one would branch across the
module boundary — a call site the single-image form cannot see.

## The codec

| tool | what it does |
|---|---|
| **`ring_sites.py`** | 4078 / 4079 / 4080 / 4070 / 4071 on MIPS, PowerPC and ARM/THUMB, in both of ARM's encodings, with every denominator |
| **`struct_probe.py`** | the structural fingerprints — refill, mask, ring, nibble split, `+3` and `+19` — in both instruction sets |
| **`nearmiss.py`** | reads every site the two scans flag, and prints the **containing ARM word** for every THUMB hit |
| **`blind_decode.py`** | the reference decoder over every payload in both dialects, with a positive control in the same invocation |
| **`tales_block.py`** | the reference decoder, copied, not reimplemented |

`blind_decode.py` was extended twice: it **walks the tree** (same `os.listdir`
problem), and it descends into **`EZBIND` members**, including the members of
archives that had to be decompressed first — which is where two thirds of this
cartridge's data lives and where a member-level census would have missed all of
it.

## Containers, media and the budget

| tool | what it does |
|---|---|
| **`formats.py`** | classifies every file by magic and arithmetic, never by extension, and accounts for every byte of the cartridge |
| **`sdat.py`** | the Nitro sound archive: blocks, `SYMB`, `INFO`, `FAT` |
| **`media_census.py`** | `STRM` and `SWAV` durations from sample counts, `VXDS` headers, and now CRI `ADX`/`AHX` and Actimagine `MODS` |
| **`magic_sweep.py`** | the corpus's markers with the chance rate printed beside every count |
| **`crosstitle.py`** | other titles' names in file names, in the image and in the **Nitro internal-name dictionaries** |
| **`leftovers.py`** | ASCII and Shift-JIS runs sorted into build stamps, SDK names, paths, debug text; and `--tree`, the file-name census |

`formats.py` gained the `EZBIND`, `MODS`, `RTFN`, `NARC`, `FaceChat`/`FaceData`
and `DSpr` magics, a CRI `ADX`/`AHX` recogniser that reads the `(c)CRI` marker
at the offset the header's own field points to, transparent decompression of
BIOS streams before classifying, and a **second census over the container
members** — printed separately rather than pro-rated into the first, because
attributing an archive's bytes to its members' classes would be an estimate
where the two tables are measurements.

`media_census.py` gained `--cri` and `--mods`. `crosstitle.py` had its
internal-name harvest extended to descend through `EZBIND` and through
compression; unextended it reads 1,516 of 6,664 Nitro payloads and reports 936
names as though that were the corpus. `leftovers.py` gained `--tree`.

---

## Reproducing every report

```sh
export PYTHONIOENCODING=utf-8
ROM="_work/Tales of Innocence (Japan).nds"

# the cartridge
python tools/ndsrom.py "$ROM"                        > reports/nds-header.txt
python tools/ndsrom.py "$ROM" --overlays             > reports/nds-overlays.txt
python tools/ndsrom.py "$ROM" --banner               > reports/nds-banner.txt
python tools/ndsrom.py "$ROM" --files                > reports/nds-files.txt
python tools/ndsrom.py "$ROM" --extract _work/fs
python tools/securearea.py "$ROM" --control _work/fs/test/op.mods --windows 3000 \
                                                     > reports/secure-area.txt
python tools/datestamps.py "$ROM"                    > reports/datestamps.txt

# the modules (arm9.bin, arm7.bin and overlay_{0,1,2}.bin extracted into _work/)
python tools/ndscomp.py --blz _work/arm9.bin /dev/null      # says it is not packed
python tools/ring_sites.py   _work/arm9.bin --arm --base 0x02000000 \
        --imm 4070,4071,4078,4079,4080               > reports/ring-sites-arm9-arm7.txt
python tools/struct_probe.py _work/arm9.bin --base 0x02000000 > reports/struct-probe.txt
python tools/nearmiss.py     _work/arm9.bin --base 0x02000000 \
        --imm 4070,4071,4078,4079,4080               > reports/near-misses.txt
python tools/lzprobe.py      _work/arm9.bin --base 0x02000000 \
                                                     > reports/lz77-decoder-probe.txt
python tools/symbols.py _work/arm9.bin _work/arm7.bin _work/overlay_*.bin --all \
                                                     > reports/symbols.txt
python tools/bios_calls.py _work/arm9.bin --base 0x02000000 \
        --also _work/overlay_0.bin@0x02120E60 \
        --also _work/overlay_1.bin@0x02120E60 \
        --also _work/overlay_2.bin@0x02120E60        > reports/bios-calls.txt
# (the four scans above are run over all five modules; see the reports)

# compression and containers
python tools/ndscomp.py --census _work/fs            > reports/bios-compression-census.txt
python tools/ndscomp.py --sweep  _work/fs --step 4   > reports/bios-stream-sweep.txt
python tools/ndscomp.py --verify _work/fs/motion/alb000/01_LZ.bin \
                                 _work/fs/motion/alb000/01.nsbca \
                                                     > reports/bios-format-control.txt
python tools/ezbind.py _work/fs --walk               > reports/ezbind-census.txt

# the codec
python tools/tales_block.py --selftest               > reports/selftest.txt
python tools/blind_decode.py --rom "$ROM" --files _work/fs \
        --control "Tales of Phantasia (Japan).sfc"   > reports/blind-decode.txt

# media, the budget and the leftovers
python tools/formats.py "$ROM" _work/fs              > reports/budget.txt
python tools/formats.py "$ROM" _work/fs --csv        > reports/file-census.csv
python tools/deflate_control.py "$ROM" _work/fs      > reports/deflate-control.txt
python tools/media_census.py --mods _work/fs/test/op.mods   > reports/media-census.txt
python tools/media_census.py --cri  _work/fs               >> reports/media-census.txt
python tools/media_census.py _work/fs/sound/ToI.sdat       >> reports/media-census.txt
python tools/sdat.py _work/fs/sound/ToI.sdat         > reports/sdat.txt
python tools/magic_sweep.py "$ROM"                   > reports/magic-sweep.txt
python tools/crosstitle.py "$ROM" _work/fs           > reports/cross-title.txt
python tools/leftovers.py _work/arm9.bin _work/arm7.bin _work/overlay_*.bin \
                                                     > reports/leftovers-exe.txt
python tools/leftovers.py --tree _work/fs --rom "$ROM" > reports/leftovers-tree.txt
```

No game data is committed to this repository. `_work/` is in `.gitignore`.
