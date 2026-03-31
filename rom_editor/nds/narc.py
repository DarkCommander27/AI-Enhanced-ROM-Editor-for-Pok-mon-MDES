"""NARC (Nintendo ARChive) file format handler.

NARC is the archive format used inside NDS ROMs to group related files.
It consists of three sections: BTAF (FAT), BTNF (FNT), and GMIF (File Image).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional


_NARC_MAGIC = b"NARC"
_BTAF_MAGIC = b"BTAF"
_BTNF_MAGIC = b"BTNF"
_GMIF_MAGIC = b"GMIF"


@dataclass
class NARCFile:
    """Represents a single file stored inside a NARC archive."""

    index: int
    name: Optional[str]
    data: bytearray

    def __len__(self) -> int:
        return len(self.data)


class NARC:
    """Parse, access, and repack NARC archives.

    Usage::

        narc = NARC.from_bytes(raw_narc_data)
        file_data = narc[0].data          # access by index
        narc[0].data = my_new_bytes       # modify in place
        repacked = narc.to_bytes()        # repack to bytes
    """

    def __init__(self, files: list[NARCFile]) -> None:
        self._files = files

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_bytes(cls, data: bytes | bytearray) -> "NARC":
        """Parse a NARC from raw bytes."""
        data = bytes(data)
        if data[:4] != _NARC_MAGIC:
            raise ValueError("Not a NARC file (missing NARC magic)")

        # NARC header: magic(4), BOM(2), version(2), filesize(4), hdrsize(2), sections(2)
        _bom, _ver, _file_size, hdr_size, num_sections = struct.unpack_from(
            "<HHIHH", data, 4
        )

        pos = hdr_size  # position after NARC header

        # --- Section 1: BTAF (File Allocation Table) ---
        if data[pos:pos + 4] != _BTAF_MAGIC:
            raise ValueError("Expected BTAF section")
        btaf_size = struct.unpack_from("<I", data, pos + 4)[0]
        num_files = struct.unpack_from("<H", data, pos + 8)[0]
        fat: list[tuple[int, int]] = []
        fat_pos = pos + 12
        for _ in range(num_files):
            start, end = struct.unpack_from("<II", data, fat_pos)
            fat.append((start, end))
            fat_pos += 8
        pos += btaf_size

        # --- Section 2: BTNF (File Name Table) ---
        if data[pos:pos + 4] != _BTNF_MAGIC:
            raise ValueError("Expected BTNF section")
        btnf_size = struct.unpack_from("<I", data, pos + 4)[0]
        fnt_data = data[pos + 8:pos + btnf_size]
        names = cls._parse_fnt(fnt_data, num_files)
        pos += btnf_size

        # --- Section 3: GMIF (Game Image File) ---
        if data[pos:pos + 4] != _GMIF_MAGIC:
            raise ValueError("Expected GMIF section")
        _gmif_size = struct.unpack_from("<I", data, pos + 4)[0]
        file_base = pos + 8

        files: list[NARCFile] = []
        for i, (start, end) in enumerate(fat):
            file_data = bytearray(data[file_base + start:file_base + end])
            files.append(NARCFile(index=i, name=names.get(i), data=file_data))

        return cls(files)

    @classmethod
    def empty(cls) -> "NARC":
        """Create an empty NARC with no files."""
        return cls([])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._files)

    def __getitem__(self, index: int) -> NARCFile:
        return self._files[index]

    def __iter__(self):
        return iter(self._files)

    @property
    def num_files(self) -> int:
        return len(self._files)

    def get_by_name(self, name: str) -> Optional[NARCFile]:
        """Return the file with the given name, or None."""
        for f in self._files:
            if f.name == name:
                return f
        return None

    def append_file(self, data: bytes | bytearray, name: Optional[str] = None) -> NARCFile:
        """Append a new file to the archive and return the created entry."""
        new_index = len(self._files)
        entry = NARCFile(index=new_index, name=name, data=bytearray(data))
        self._files.append(entry)
        return entry

    def to_bytes(self) -> bytes:
        """Repack the NARC archive to bytes."""
        # Build GMIF (file image) and FAT entries
        file_images = b""
        fat_entries: list[tuple[int, int]] = []
        for f in self._files:
            start = len(file_images)
            end = start + len(f.data)
            fat_entries.append((start, end))
            file_images += bytes(f.data)
            # 4-byte align
            if len(file_images) % 4:
                file_images += b"\xFF" * (4 - len(file_images) % 4)

        # --- BTAF section ---
        num_files = len(self._files)
        btaf_data = struct.pack("<HH", num_files, 0)  # count + padding
        for start, end in fat_entries:
            btaf_data += struct.pack("<II", start, end)
        btaf_size = 8 + len(btaf_data)
        btaf_section = _BTAF_MAGIC + struct.pack("<I", btaf_size) + btaf_data

        # --- BTNF section ---
        # Minimal FNT: just a root entry with offset 4 and first_file=0
        btnf_payload = struct.pack("<IHH", 4, 0, 1)  # sub_offset, first_file, parent
        btnf_size = 8 + len(btnf_payload)
        btnf_section = _BTNF_MAGIC + struct.pack("<I", btnf_size) + btnf_payload

        # --- GMIF section ---
        gmif_size = 8 + len(file_images)
        gmif_section = _GMIF_MAGIC + struct.pack("<I", gmif_size) + file_images

        # --- NARC header ---
        body = btaf_section + btnf_section + gmif_section
        narc_header_size = 16
        total_size = narc_header_size + len(body)
        narc_header = (
            _NARC_MAGIC
            + struct.pack("<HH", 0xFFFE, 0x0100)  # BOM, version
            + struct.pack("<IHH", total_size, narc_header_size, 3)  # size, hdrsize, sections
        )
        return narc_header + body

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_fnt(fnt_data: bytes, num_files: int) -> dict[int, str]:
        """Parse BTNF data and return {file_index: name}."""
        names: dict[int, str] = {}
        if len(fnt_data) < 8:
            return names
        try:
            sub_offset, first_file, _parent = struct.unpack_from("<IHH", fnt_data, 0)
            pos = sub_offset
            cur_id = first_file
            while pos < len(fnt_data):
                if pos >= len(fnt_data):
                    break
                type_len = fnt_data[pos]
                if type_len == 0:
                    break
                pos += 1
                is_dir = bool(type_len & 0x80)
                name_len = type_len & 0x7F
                if pos + name_len > len(fnt_data):
                    break
                name = fnt_data[pos:pos + name_len].decode("ascii", errors="replace")
                pos += name_len
                if is_dir:
                    pos += 2  # skip child dir id
                else:
                    names[cur_id] = name
                    cur_id += 1
        except struct.error:
            pass
        return names
