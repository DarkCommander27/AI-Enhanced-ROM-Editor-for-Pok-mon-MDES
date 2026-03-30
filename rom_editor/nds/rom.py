"""NDS ROM header and file-system parser.

Supports reading the Nintendo DS ROM format including:
- ROM header (512 bytes)
- File Name Table (FNT)
- File Allocation Table (FAT)
- Individual file extraction and replacement
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# NDS Header layout (512 bytes, offsets per GBATEK)
# https://problemkaputt.de/gbatek.htm#dscartridgeheader
# ---------------------------------------------------------------------------
_HDR_SIZE = 0x200  # 512 bytes

_HEADER_STRUCT = struct.Struct(
    "<"
    "12s"   # 0x000 game title (12 bytes ASCII, NUL-padded)
    "4s"    # 0x00C game code
    "2s"    # 0x010 maker code
    "B"     # 0x012 unit code (0=NDS, 2=NDS+DSi, 3=DSi)
    "B"     # 0x013 encryption seed select
    "B"     # 0x014 device capacity
    "8s"    # 0x015 reserved (7 bytes) + region code (1 byte)
    "B"     # 0x01D ROM version
    "B"     # 0x01E autostart flags
    "x"     # 0x01F reserved
    "I"     # 0x020 ARM9 ROM offset
    "I"     # 0x024 ARM9 entry address
    "I"     # 0x028 ARM9 RAM address
    "I"     # 0x02C ARM9 size
    "I"     # 0x030 ARM7 ROM offset
    "I"     # 0x034 ARM7 entry address
    "I"     # 0x038 ARM7 RAM address
    "I"     # 0x03C ARM7 size
    "I"     # 0x040 FNT offset
    "I"     # 0x044 FNT size
    "I"     # 0x048 FAT offset
    "I"     # 0x04C FAT size
    "I"     # 0x050 ARM9 overlay offset
    "I"     # 0x054 ARM9 overlay size
    "I"     # 0x058 ARM7 overlay offset
    "I"     # 0x05C ARM7 overlay size
    "I"     # 0x060 control register flags (normal commands)
    "I"     # 0x064 control register flags (KEY1 commands)
    "I"     # 0x068 icon / title offset
    "H"     # 0x06C secure area CRC16
    "H"     # 0x06E secure area loading timeout
    "I"     # 0x070 ARM9 auto-load list hook RAM address
    "I"     # 0x074 ARM7 auto-load list hook RAM address
    "Q"     # 0x078 secure area disable (8 bytes)
    "I"     # 0x080 total ROM size
    "I"     # 0x084 ROM header size
    "56s"   # 0x088 reserved
    "156s"  # 0x0C0 Nintendo logo
    "H"     # 0x15C Nintendo logo CRC16
    "H"     # 0x15E header CRC16
)


@dataclass
class NDSHeader:
    """Parsed NDS ROM header fields."""

    game_title: str
    game_code: str
    maker_code: str
    unit_code: int
    encryption_seed: int
    device_capacity: int
    rom_version: int
    autostart: int
    arm9_rom_offset: int
    arm9_entry_address: int
    arm9_ram_address: int
    arm9_size: int
    arm7_rom_offset: int
    arm7_entry_address: int
    arm7_ram_address: int
    arm7_size: int
    fnt_offset: int
    fnt_size: int
    fat_offset: int
    fat_size: int
    arm9_overlay_offset: int
    arm9_overlay_size: int
    arm7_overlay_offset: int
    arm7_overlay_size: int
    total_rom_size: int
    header_size: int
    header_checksum: int

    @classmethod
    def from_bytes(cls, data: bytes) -> "NDSHeader":
        """Parse an NDS header from raw bytes (must be >= 512 bytes)."""
        if len(data) < _HDR_SIZE:
            raise ValueError(f"Data too short for NDS header: {len(data)} bytes")
        fields = _HEADER_STRUCT.unpack_from(data, 0)
        (
            raw_title, raw_code, raw_maker, unit_code, enc_seed, dev_cap,
            _reserved, rom_ver, autostart,
            arm9_rom, arm9_entry, arm9_ram, arm9_size,
            arm7_rom, arm7_entry, arm7_ram, arm7_size,
            fnt_off, fnt_sz, fat_off, fat_sz,
            arm9_ov_off, arm9_ov_sz, arm7_ov_off, arm7_ov_sz,
            ctrl_flags, _key1_flags, _icon_offset,
            _secure_crc, _secure_timeout,
            arm9_al, arm7_al, secure_dis,
            total_size, hdr_size,
            _reserved2, _logo, logo_crc, hdr_crc,
        ) = fields
        return cls(
            game_title=raw_title.rstrip(b"\x00").decode("ascii", errors="replace"),
            game_code=raw_code.decode("ascii", errors="replace"),
            maker_code=raw_maker.decode("ascii", errors="replace"),
            unit_code=unit_code,
            encryption_seed=enc_seed,
            device_capacity=dev_cap,
            rom_version=rom_ver,
            autostart=autostart,
            arm9_rom_offset=arm9_rom,
            arm9_entry_address=arm9_entry,
            arm9_ram_address=arm9_ram,
            arm9_size=arm9_size,
            arm7_rom_offset=arm7_rom,
            arm7_entry_address=arm7_entry,
            arm7_ram_address=arm7_ram,
            arm7_size=arm7_size,
            fnt_offset=fnt_off,
            fnt_size=fnt_sz,
            fat_offset=fat_off,
            fat_size=fat_sz,
            arm9_overlay_offset=arm9_ov_off,
            arm9_overlay_size=arm9_ov_sz,
            arm7_overlay_offset=arm7_ov_off,
            arm7_overlay_size=arm7_ov_sz,
            total_rom_size=total_size,
            header_size=hdr_size,
            header_checksum=hdr_crc,
        )


@dataclass
class FileEntry:
    """A single file within an NDS ROM."""

    file_id: int
    name: str
    parent_path: str
    start_offset: int
    end_offset: int

    @property
    def size(self) -> int:
        return self.end_offset - self.start_offset

    @property
    def full_path(self) -> str:
        if self.parent_path and self.parent_path != "/":
            return f"{self.parent_path}/{self.name}"
        return f"/{self.name}"


class NDSRom:
    """Loads and provides access to files within an NDS ROM image.

    Usage::

        rom = NDSRom.load("game.nds")
        data = rom.read_file("/BALANCE/waza_p.bin")
        rom.write_file("/BALANCE/waza_p.bin", modified_data)
        rom.save("game_modified.nds")
    """

    def __init__(self, path: Path, data: bytearray, header: NDSHeader,
                 files: dict[str, FileEntry]) -> None:
        self._path = path
        self._data = data
        self.header = header
        self._files: dict[str, FileEntry] = files
        self._overlays: dict[str, bytes] = {}

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> "NDSRom":
        """Load an NDS ROM from *path*."""
        path = Path(path)
        raw = bytearray(path.read_bytes())
        header = NDSHeader.from_bytes(raw)
        files = cls._parse_filesystem(raw, header)
        return cls(path, raw, header, files)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    def list_files(self) -> list[str]:
        """Return all file paths in the ROM."""
        return sorted(self._files.keys())

    def has_file(self, path: str) -> bool:
        """Return True if *path* exists in the ROM."""
        return self._normalise(path) in self._files

    def read_file(self, path: str) -> bytes:
        """Read raw bytes of a file by its internal path."""
        key = self._normalise(path)
        if key not in self._files:
            raise KeyError(f"File not found in ROM: {path!r}")
        entry = self._files[key]
        return bytes(self._data[entry.start_offset:entry.end_offset])

    def write_file(self, path: str, new_data: bytes) -> None:
        """Replace a file's content in-memory (new_data must be same size).

        For simplicity this editor requires that replacement data is the same
        size as the original.  The NARC handler handles internal re-packing
        when NARC files are edited.
        """
        key = self._normalise(path)
        if key not in self._files:
            raise KeyError(f"File not found in ROM: {path!r}")
        entry = self._files[key]
        if len(new_data) != entry.size:
            raise ValueError(
                f"Size mismatch for {path!r}: "
                f"original={entry.size}, new={len(new_data)}"
            )
        self._data[entry.start_offset:entry.end_offset] = new_data

    def save(self, dest: str | Path | None = None) -> None:
        """Write the (possibly modified) ROM to *dest*.

        If *dest* is None the ROM is saved back to its original path.
        """
        out = Path(dest) if dest is not None else self._path
        out.write_bytes(self._data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return path.upper()

    @classmethod
    def _parse_filesystem(
        cls, data: bytearray, hdr: NDSHeader
    ) -> dict[str, FileEntry]:
        """Parse the FAT and FNT to build a path→FileEntry mapping."""
        fat = cls._parse_fat(data, hdr)
        dirs = cls._parse_fnt(data, hdr)
        files: dict[str, FileEntry] = {}
        for file_id, (start, end) in fat.items():
            name, parent = dirs.get(file_id, ("", "/"))
            entry = FileEntry(
                file_id=file_id,
                name=name,
                parent_path=parent,
                start_offset=start,
                end_offset=end,
            )
            key = NDSRom._normalise(entry.full_path)
            files[key] = entry
        return files

    @staticmethod
    def _parse_fat(data: bytearray, hdr: NDSHeader) -> dict[int, tuple[int, int]]:
        """Return {file_id: (start, end)} from the File Allocation Table."""
        fat: dict[int, tuple[int, int]] = {}
        num_files = hdr.fat_size // 8
        for i in range(num_files):
            offset = hdr.fat_offset + i * 8
            start, end = struct.unpack_from("<II", data, offset)
            fat[i] = (start, end)
        return fat

    @staticmethod
    def _parse_fnt(data: bytearray, hdr: NDSHeader) -> dict[int, tuple[str, str]]:
        """Return {file_id: (filename, parent_path)} from the File Name Table."""
        result: dict[int, tuple[str, str]] = {}
        fnt_base = hdr.fnt_offset

        # Root directory table entry
        root_offset, root_first_id = struct.unpack_from("<IH", data, fnt_base)
        num_dirs_raw = struct.unpack_from("<H", data, fnt_base + 6)[0]
        num_dirs = num_dirs_raw & 0x0FFF

        # Build directory paths first
        dir_paths: dict[int, str] = {0xF000: "/"}
        dir_info: dict[int, tuple[int, int]] = {}  # dir_id: (sub_table_offset, first_id)

        for d in range(num_dirs):
            entry_off = fnt_base + d * 8
            sub_off, first_id, parent_raw = struct.unpack_from("<IHH", data, entry_off)
            dir_info[0xF000 + d] = (sub_off, first_id)

        def build_path(dir_id: int) -> str:
            if dir_id == 0xF000:
                return "/"
            if dir_id in dir_paths:
                return dir_paths[dir_id]
            return "/"

        # Two-pass: first pass builds dir names, second assigns file names
        # Pass 1: assign directory names relative to root
        for d in range(1, num_dirs):
            dir_id = 0xF000 + d
            # Find the dir name by scanning parent dirs
            # For simplicity, scan all directories to find this one
            for parent_id, (parent_sub_off, parent_first) in dir_info.items():
                pos = fnt_base + parent_sub_off
                cur_file = parent_first
                while pos < fnt_base + hdr.fnt_size:
                    type_len = data[pos]
                    if type_len == 0:
                        break
                    pos += 1
                    is_dir = bool(type_len & 0x80)
                    name_len = type_len & 0x7F
                    if pos + name_len > len(data):
                        break
                    name = data[pos:pos + name_len].decode("ascii", errors="replace")
                    pos += name_len
                    if is_dir:
                        child_id = struct.unpack_from("<H", data, pos)[0]
                        pos += 2
                        if child_id == dir_id:
                            parent_path = build_path(parent_id)
                            if parent_path == "/":
                                dir_paths[dir_id] = f"/{name}"
                            else:
                                dir_paths[dir_id] = f"{parent_path}/{name}"
                    else:
                        cur_file += 1

        # Pass 2: enumerate files in each directory
        for dir_id, (sub_off, first_file_id) in dir_info.items():
            parent_path = dir_paths.get(dir_id, "/")
            pos = fnt_base + sub_off
            cur_file = first_file_id
            while pos < fnt_base + hdr.fnt_size:
                type_len = data[pos]
                if type_len == 0:
                    break
                pos += 1
                is_dir = bool(type_len & 0x80)
                name_len = type_len & 0x7F
                if pos + name_len > len(data):
                    break
                name = data[pos:pos + name_len].decode("ascii", errors="replace")
                pos += name_len
                if is_dir:
                    pos += 2  # skip child dir ID
                else:
                    result[cur_file] = (name, parent_path)
                    cur_file += 1
        return result
