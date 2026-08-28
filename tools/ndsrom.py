#!/usr/bin/env python3
"""Nintendo DS cartridge reader: header, FNT/FAT, overlay tables, banner.

Everything here is read from the image's own structures. Nothing is taken
from the file name, from a database, or from any catalogue.

  python ndsrom.py IMAGE                 header + counts
  python ndsrom.py IMAGE --files         one line per file, with names
  python ndsrom.py IMAGE --overlays      overlay table entries
  python ndsrom.py IMAGE --banner        banner: version, titles, CRC
  python ndsrom.py IMAGE --extract DIR   write every FAT file out under DIR

Standard library only.
"""
import os
import struct
import sys

HDR_FIELDS = [
    ("arm9_rom_off", 0x20), ("arm9_entry", 0x24), ("arm9_ram", 0x28), ("arm9_size", 0x2C),
    ("arm7_rom_off", 0x30), ("arm7_entry", 0x34), ("arm7_ram", 0x38), ("arm7_size", 0x3C),
    ("fnt_off", 0x40), ("fnt_size", 0x44), ("fat_off", 0x48), ("fat_size", 0x4C),
    ("arm9_ovt_off", 0x50), ("arm9_ovt_size", 0x54),
    ("arm7_ovt_off", 0x58), ("arm7_ovt_size", 0x5C),
    ("normal_cmd_setting", 0x60), ("key1_cmd_setting", 0x64),
    ("banner_off", 0x68),
    ("arm9_autoload", 0x70), ("arm7_autoload", 0x74),
    ("ntr_rom_size", 0x80), ("header_size", 0x84),
]

# The value the Nintendo logo bitmap's CRC has on every retail cartridge.
NINTENDO_LOGO_CRC = 0xCF56


def crc16(data, init=0xFFFF):
    """The CRC-16 the cartridge header uses (poly 0xA001, reflected)."""
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


class NDS(object):
    def __init__(self, data):
        self.d = data
        self.hdr = {}
        for name, off in HDR_FIELDS:
            self.hdr[name] = struct.unpack_from("<I", data, off)[0]
        self.title = data[0x00:0x0C].rstrip(b"\x00")
        self.gamecode = data[0x0C:0x10]
        self.makercode = data[0x10:0x12]
        self.unitcode = data[0x12]
        self.encryption_seed = data[0x13]
        self.devicecap = data[0x14]
        self.reserved_15 = data[0x15:0x1D]
        self.region = data[0x1D]
        self.romversion = data[0x1E]
        self.autostart = data[0x1F]
        self.secure_crc = struct.unpack_from("<H", data, 0x6C)[0]
        self.secure_timeout = struct.unpack_from("<H", data, 0x6E)[0]
        self.secure_disable = data[0x78:0x80]
        self.logo = data[0xC0:0x15C]
        self.logo_crc = struct.unpack_from("<H", data, 0x15C)[0]
        self.header_crc = struct.unpack_from("<H", data, 0x15E)[0]
        self.debug = data[0x160:0x180]

    @property
    def capacity_bytes(self):
        return 128 * 1024 << self.devicecap

    def header_crc_ok(self):
        return crc16(self.d[0x00:0x15E]) == self.header_crc

    def logo_crc_ok(self):
        return crc16(self.logo) == self.logo_crc

    # ---- FAT ------------------------------------------------------------
    def fat(self):
        off, size = self.hdr["fat_off"], self.hdr["fat_size"]
        out = []
        for i in range(size // 8):
            s, e = struct.unpack_from("<II", self.d, off + i * 8)
            out.append((s, e))
        return out

    # ---- FNT ------------------------------------------------------------
    def fnt(self):
        """Return (files, dirs).

        files: list of (fat_id, full_path)
        dirs:  list of (dir_id, full_path)
        """
        base = self.hdr["fnt_off"]
        if base == 0 or self.hdr["fnt_size"] == 0:
            return [], []
        _, _, ndirs = struct.unpack_from("<IHH", self.d, base)
        files, dirs = [], []
        for i in range(ndirs):
            sub, first_id, _par = struct.unpack_from("<IHH", self.d, base + i * 8)
            p = base + sub
            fid = first_id
            while True:
                t = self.d[p]
                p += 1
                if t == 0:
                    break
                if t < 0x80:
                    nm = self.d[p:p + t].decode("shift_jis", "replace")
                    p += t
                    files.append((fid, i, nm))
                    fid += 1
                else:
                    ln = t & 0x7F
                    nm = self.d[p:p + ln].decode("shift_jis", "replace")
                    p += ln
                    did = struct.unpack_from("<H", self.d, p)[0] & 0xFFF
                    p += 2
                    dirs.append((did, i, nm))
        dname = {0: ""}
        changed = True
        while changed:
            changed = False
            for did, par, nm in dirs:
                if did not in dname and par in dname:
                    dname[did] = dname[par] + "/" + nm
                    changed = True
        out_files = [(fid, dname.get(par, "/?") + "/" + nm) for fid, par, nm in files]
        out_dirs = [(did, dname.get(did, "/?")) for did, _, _ in dirs]
        return sorted(out_files), sorted(out_dirs)

    # ---- overlays -------------------------------------------------------
    def overlays(self, cpu=9):
        off = self.hdr["arm9_ovt_off" if cpu == 9 else "arm7_ovt_off"]
        size = self.hdr["arm9_ovt_size" if cpu == 9 else "arm7_ovt_size"]
        out = []
        for i in range(size // 32):
            (oid, ram, ram_size, bss, sinit_s, sinit_e, fid,
             flags) = struct.unpack_from("<8I", self.d, off + i * 32)
            out.append(dict(id=oid, ram=ram, ram_size=ram_size, bss=bss,
                            static_init=(sinit_s, sinit_e), file_id=fid,
                            compressed_size=flags & 0xFFFFFF,
                            compressed=bool(flags & 0x1000000)))
        return out

    # ---- banner ---------------------------------------------------------
    def banner(self):
        off = self.hdr["banner_off"]
        if off == 0:
            return None
        ver = struct.unpack_from("<H", self.d, off)[0]
        crc = struct.unpack_from("<H", self.d, off + 2)[0]
        sizes = {1: 0x840, 2: 0x940, 3: 0xA40, 0x103: 0x23C0}
        blen = sizes.get(ver, 0x840)
        titles = {}
        langs = ["ja", "en", "fr", "de", "it", "es", "zh", "ko"]
        ntitle = {1: 6, 2: 7, 3: 8, 0x103: 8}.get(ver, 6)
        for i in range(ntitle):
            raw = self.d[off + 0x240 + i * 0x100: off + 0x240 + (i + 1) * 0x100]
            titles[langs[i]] = raw.decode("utf-16-le", "replace").split("\x00")[0]
        return dict(offset=off, version=ver, crc=crc, size=blen, titles=titles,
                    crc_ok=(crc16(self.d[off + 0x20:off + 0x840]) == crc))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    data = open(path, "rb").read()
    r = NDS(data)
    args = sys.argv[2:]

    if "--files" in args:
        files, dirs = r.fnt()
        fat = r.fat()
        print("# %d directories" % len(dirs))
        for did, p in dirs:
            print("# dir %3d  %s" % (did, p or "/"))
        print("# fat_id\tstart\tend\tsize\tpath")
        for fid, p in files:
            s, e = fat[fid] if fid < len(fat) else (0, 0)
            print("%d\t%d\t%d\t%d\t%s" % (fid, s, e, e - s, p))
        return 0
    if "--overlays" in args:
        for cpu in (9, 7):
            ov = r.overlays(cpu)
            print("# ARM%d overlay table: %d entries" % (cpu, len(ov)))
            for o in ov:
                print("  ovl %3d  file %4d  ram 0x%08X  size %7d  bss %6d  "
                      "compressed %s (%d)" % (o["id"], o["file_id"], o["ram"],
                                              o["ram_size"], o["bss"],
                                              o["compressed"], o["compressed_size"]))
        return 0
    if "--banner" in args:
        b = r.banner()
        print("banner offset  0x%X" % b["offset"])
        print("banner version 0x%04X" % b["version"])
        print("banner crc     0x%04X  (recomputed: %s)"
              % (b["crc"], "OK" if b["crc_ok"] else "MISMATCH"))
        for k, v in b["titles"].items():
            print("  %-3s %r" % (k, v))
        return 0
    if "--extract" in args:
        out = args[args.index("--extract") + 1]
        files, _ = r.fnt()
        fat = r.fat()
        seen = set(f for f, _ in files)
        for fid, p in files:
            s, e = fat[fid]
            dst = os.path.join(out, p.lstrip("/").replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(data[s:e])
        for fid, (s, e) in enumerate(fat):
            if fid in seen:
                continue
            dst = os.path.join(out, "_unnamed", "fat%04d.bin" % fid)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(data[s:e])
        print("extracted %d named + %d unnamed" % (len(files), len(fat) - len(seen)))
        return 0

    files, dirs = r.fnt()
    fat = r.fat()
    used = max((e for _, e in fat), default=0)
    print("image                %s" % os.path.basename(path))
    print("file size            %d bytes" % len(data))
    print("")
    print("game title           %r" % r.title.decode("ascii", "replace"))
    print("game code            %r" % r.gamecode.decode("ascii", "replace"))
    print("maker code           %r" % r.makercode.decode("ascii", "replace"))
    print("unit code            0x%02X" % r.unitcode)
    print("encryption seed      0x%02X" % r.encryption_seed)
    print("device capacity      0x%02X  = %d bytes" % (r.devicecap, r.capacity_bytes))
    print("reserved +0x15..1C   %s" % r.reserved_15.hex())
    print("region byte          0x%02X" % r.region)
    print("ROM version          0x%02X" % r.romversion)
    print("autostart            0x%02X" % r.autostart)
    print("")
    for name, off in HDR_FIELDS:
        print("%-20s 0x%08X  (%d)" % (name, r.hdr[name], r.hdr[name]))
    print("")
    print("secure area CRC      0x%04X" % r.secure_crc)
    print("secure area delay    0x%04X" % r.secure_timeout)
    print("secure area disable  %s" % r.secure_disable.hex())
    print("logo CRC             0x%04X  (recomputed 0x%04X, %s; retail value 0x%04X)"
          % (r.logo_crc, crc16(r.logo), "OK" if r.logo_crc_ok() else "MISMATCH",
             NINTENDO_LOGO_CRC))
    print("header CRC           0x%04X  (recomputed 0x%04X, %s)"
          % (r.header_crc, crc16(r.d[0x00:0x15E]),
             "OK" if r.header_crc_ok() else "MISMATCH"))
    print("debug +0x160..17F    %s" % r.debug.hex())
    print("")
    print("FAT entries          %d" % len(fat))
    print("named files          %d" % len(files))
    print("directories          %d" % len(dirs))
    print("ARM9 overlays        %d" % len(r.overlays(9)))
    print("ARM7 overlays        %d" % len(r.overlays(7)))
    print("highest FAT end      %d (0x%X)" % (used, used))
    print("declared used size   %d (0x%X)" % (r.hdr["ntr_rom_size"], r.hdr["ntr_rom_size"]))
    print("trailing bytes       %d (%.2f%% of the cartridge)"
          % (len(data) - used, 100.0 * (len(data) - used) / len(data)))
    tail = data[used:]
    print("trailing byte values %s" % sorted(set(tail))[:8])
    b = r.banner()
    if b:
        print("")
        print("banner version       0x%04X at 0x%X, CRC %s"
              % (b["version"], b["offset"], "OK" if b["crc_ok"] else "MISMATCH"))
        for k, v in b["titles"].items():
            print("  title[%s]           %r" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
