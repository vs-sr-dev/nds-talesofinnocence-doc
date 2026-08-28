# 09 — Leftovers

What got shipped that was not meant to be read.
[`leftovers.py`](../tools/leftovers.py), [`symbols.py`](../tools/symbols.py),
[`datestamps.py`](../tools/datestamps.py), [`ezbind.py`](../tools/ezbind.py).
[`reports/leftovers-exe.txt`](../reports/leftovers-exe.txt),
[`reports/leftovers-tree.txt`](../reports/leftovers-tree.txt),
[`reports/symbols.txt`](../reports/symbols.txt),
[`reports/datestamps.txt`](../reports/datestamps.txt).

---

## The biggest one: a `dir` listing, shipped inside the game

`/battle/list`, 14,109 bytes, is the captured standard output of a Windows
`dir` command, in Shift-JIS, complete with the volume header and the free-space
footer:

```
 ドライブ D のボリューム ラベルがありません。
 ボリューム シリアル番号は 1E3D-16E6 です

 D:\toi\resorce\archive のディレクトリ

2006/12/05  16:56    <DIR>          .
2006/12/05  16:56    <DIR>          ..
2006/12/05  18:34                 0 list
2006/12/05  17:54                16 bst066_mdl.bin
2006/12/05  18:27                16 toi100_mot.bin
        ...
2006/12/05  18:26           357,508 bst042_mot.bin
             265 個のファイル           7,476,356 バイト
               2 個のディレクトリ  10,851,483,648 バイトの空き領域
```

Somebody typed `dir > list` in the battle asset directory on **5 December
2006**, the file was picked up by the build with everything else in the folder,
and it shipped. It gives, for free:

* the **project directory name**, `toi`, matching the `cToi*` class prefix in
  the executables and the `TOIBACKUP` save signature;
* the misspelling `resorce`, which occurs exactly once in 134,217,728 bytes;
* the drive letter and volume serial of a build machine;
* 265 asset file names with their sizes and timestamps at a moment a year
  before release, several of which — `toi090_mot.bin`, `toi100_mot.bin`,
  `bst066_mdl.bin` — are **16 bytes**, i.e. empty placeholder archives;
* 10.85 GB free on `D:`.

*Tales of the Tempest*'s equivalent leftover was two 3ds Max `.imd`
intermediates carrying artists' user names, host names and desktop paths. This
is a different accident with the same shape, and it is the only Windows path on
the cartridge — the executables contain none.

---

## The compression benchmark

`/motion/alb000/` contains, beside `00.nsbca` (3,376 bytes) and `01.nsbca`
(6,736 bytes), six files that are those two animations compressed:

| file | bytes | format | decodes to |
|---|---:|---|---|
| `00_HUFF.bin` | 3,296 | Huffman 8-bit | `00.nsbca`, byte for byte |
| `01_LZ.bin` | 6,174 | `LZ77` | `01.nsbca`, byte for byte |
| `01_HUFF.bin` | 6,108 | Huffman 4-bit | `01.nsbca`, byte for byte |
| `01_RL.bin` | 6,657 | `RLE` | `01.nsbca`, byte for byte |
| `01_DIFF.bin` | 6,740 | difference filter, 16-bit | `01.nsbca`, byte for byte |

Somebody was choosing a compressor, kept every candidate and the input, and the
directory went into the build. It is the **only positive control this corpus
has ever had** for the DS BIOS formats, and running it found two real defects in
`ndscomp.py` ([06](06-what-it-uses-instead.md)).

---

## Test and placeholder content

[`leftovers.py --tree`](../tools/leftovers.py).

| | files | bytes |
|---|---:|---:|
| names containing `test`, `dbg`, `debug`, `dummy`, `sample`, `copy`, or starting `_` | **199** | **13,452,542** (10.57% of the file bytes) |
| the same test on `EZBIND` **members** | **1,023** | **2,799,528** |

The headline number needs splitting, because two of the 199 are not leftovers
at all. `/test/op.mods` is the **only** Mobiclip file on the cartridge and
`/test/ed.adx` is the **only** stereo CRI stream and the only one longer than
53 seconds — three minutes exactly — beside thirteen `/staff/ed01…ed13.bin`
image sequences and a credit roll naming an opening and an ending theme. They
are the opening movie and the ending song, 10,683,118 bytes between them, and
the directory name is the leftover rather than the content. Take them out and
the genuine test content is **197 files and 2,769,424 bytes, 2.2% of the file
area**.

Almost all of it is one thing: **`/world/f_test04_Room_00` … `_79`**, 196
archives and 2,720,448 bytes, which is 98% of the `world` directory. Each is an
`EZBIND` holding a `.nsbmd` model, a `.nsbta` texture animation, an `_attr.dat`
and an `_attr_area.dat` collision pair, and a sixteen-byte `.boxtest`. The four
files in `/world` that are not `f_test04` are `WorldMap.dat`, `WorldArea.dat`,
`world2d.bin` and `worldtex.bin`. So the **entire world-map room set on the
retail cartridge is named after a test scene** — either the test scene became
the shipping content and kept its name, or the shipping content never displaced
it. The image does not say which.

The rest: `/chara/dummy.bin` at 48,976 bytes, `/chara/symbol__mot.bin` holding a
four-byte `dummy.dat`, and scattered `_tmp` members.

Beside *Tales of the Tempest*: 96 files and 4,373,708 bytes, 5.78% of that
cartridge, including five complete debug fields with night variants and a
working scene-select menu with a gold, item, level and title editor attached.
**Innocence has nothing of that kind.** No debug menu, no scene select, no
editor — the search for one returns nothing but the name census above. Tempest
could afford its debug build because 41.3% of the cartridge was empty; this one
has 3.2% spare.

---

## The credits, as text

`/staff/staff.bin` is an `EZBIND` with two members: `staff.nftr`, a font, and
**`list.txt`, 4,955 bytes of plain Shift-JIS**. It is the whole credit roll,
extractable in one line, and it contains:

* the full Japanese voice cast, role by role;
* the animation production credits, with `*logo0` standing in where a studio
  logo image is substituted;
* the opening and ending themes — **`Follow the Nightingale`** and
  **`say goodbye good day`**, both by KOKIA, arranged by 澤近泰輔;
* a block headed **`アルファ・システム　スタッフ`** naming **thirty** people
  under headings that are themselves informative — プロセスマネージャー,
  メインプログラム, バトルプログラム, エフェクトプログラム,
  メニュープログラム, イベントプログラム;
* a block headed **`バンダイナムコゲームス　スタッフ`**;
* and 株式会社クリーク・アンド・リバー社 between them.

This is the fifth distinct behaviour the corpus has seen from a *Tales* build's
credits, and it is the most legible: *Rebirth* romanised its whole cast into
English, *Legendia* carried no cast names at all, *Abyss* carried its entire
tracklist in English and no cast, *Tempest* shipped its credits as **32 tile
sets with no readable text anywhere**, and this one ships a text file.
[08](08-cross-title.md).

---

## English in a Japan-only release

Little, and all of it is a proper noun. Two song titles in the credits, the
header line `Tales of Innocence Staff`, `KOKIA` four times, the SDK component
strings, the CRI build strings, `(c)CRI` 4,800 times (once per audio stream and
then some), and the class names — which are all English, because C++ identifiers
are. There is no English UI text, no `PRESS START`, no `GAME OVER`.

---

## Format strings, which say what the loader does

The ARM9's diagnostic strings are the clearest statement of how the file system
is used, and they are why the "4,591 unmentioned file names" figure in
[07](07-media-and-budget.md) is not a count of dead files:

```
facechat/ev%04d.scr        battle/%s_mdl.bin      Item%03d.nbfc
facechat/sb%02d-%04d.scr   battle/%s_tex.bin      Weapon%03d.nbfc
chara%02d.nbfc             battle/%s_mot.bin      Armor%03d.nbfc
chara/symbol_%s_mot.bin    btmap_%03d             Accessory%02d.nbfc
%s_sotai.nsbmd / .nsbtx / .nsbta                  Recipe%03d.nbfc
```

Most of the cartridge is addressed by a name the code builds at run time.

## The NitroSDK wireless sample, again

The ARM9 carries the SDK's `WH_` / `WM_` wireless helper with its `printf`
strings intact — `StartParent - new child (aid 0x%x) connected`,
`WH_StateOutStartScan : MAC=%02x%02x%02x%02x%02x%02x`, `decided channel = %d`,
`WM_ERRCODE_FIFO_ERROR` and thirty more — plus `cToiWirelessResult`,
`cToiTitleConnectionMenu` and a `18cToiWirelessResult` whose neighbours in the
string pool are the Japanese debug values `無し`, `試し５５` ("test 55") and
`適当` ("whatever"). *Tales of the Tempest* shipped the same SDK sample with the
same `printf`s; two DS cartridges, two studios, the same library left
uncleaned.

## The save format

`arm9.bin+0xA4479`, in UTF-16, twice:

```
TOIBACKUP:2007/10/07.0000021
```

beside the type names `cToiBackupFile`, `cDSMainMemoryImage`, `iDSMemoryImage`
and `iSavable`. A date and a revision number frozen into the backup signature,
which is the only thing on the cartridge that dates the *game's own code*
([02](02-cartridge-and-header.md)).

## A quest table in plain text

`/quest/questdata.txt`, 20,726 bytes, begins `TOI_QUEST_DATA` and is a
line-oriented table of quest records in Shift-JIS — reward counts, item ids,
Japanese quest names such as 苗木 and 漢方薬の材料 — with `modelname_tmp` and
empty `""` fields still in it. Shipped as text, parsed at run time, and the
placeholder strings were never filled in.
