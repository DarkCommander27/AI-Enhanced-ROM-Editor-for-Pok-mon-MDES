"""Tests for the NDS ROM header parser and filesystem."""

from __future__ import annotations

import struct
import pytest

from rom_editor.nds.rom import NDSHeader, _HDR_SIZE


def _make_nds_header(
    game_title: str = "POKEMON MD SKY",
    game_code: str = "YOTE",
    maker_code: str = "01",
    fnt_offset: int = 0x4000,
    fnt_size: int = 0x100,
    fat_offset: int = 0x4200,
    fat_size: int = 0x200,
    total_size: int = 0x200000,
) -> bytes:
    """Build a minimal 512-byte NDS header by setting fields at known offsets.

    Rather than using the full _HEADER_STRUCT.pack() (which is fragile),
    we write directly to a bytearray at the documented NDS header offsets.
    """
    buf = bytearray(_HDR_SIZE)  # 512 zero bytes

    # 0x000  Game title (12 bytes ASCII, NUL-padded)
    title_bytes = game_title.encode("ascii")[:12].ljust(12, b"\x00")
    buf[0x000:0x00C] = title_bytes

    # 0x00C  Game code (4 bytes ASCII)
    buf[0x00C:0x010] = game_code.encode("ascii")[:4]

    # 0x010  Maker code (2 bytes ASCII)
    buf[0x010:0x012] = maker_code.encode("ascii")[:2].ljust(2, b"\x00")

    # 0x012  Unit code = 1 (NDS)
    buf[0x012] = 1

    # 0x040  FNT offset / size (GBATEK standard)
    struct.pack_into("<II", buf, 0x040, fnt_offset, fnt_size)

    # 0x048  FAT offset / size (GBATEK standard)
    struct.pack_into("<II", buf, 0x048, fat_offset, fat_size)

    # 0x080  Total ROM size (GBATEK standard)
    struct.pack_into("<I", buf, 0x080, total_size)

    return bytes(buf)


class TestNDSHeader:
    def test_parse_game_code(self):
        raw = _make_nds_header(game_code="YOTE")
        hdr = NDSHeader.from_bytes(raw)
        assert hdr.game_code == "YOTE"

    def test_parse_game_title(self):
        raw = _make_nds_header(game_title="POKEMON MD SKY")
        hdr = NDSHeader.from_bytes(raw)
        assert "POKEMON" in hdr.game_title

    def test_parse_fat_offset(self):
        raw = _make_nds_header(fat_offset=0x4200, fat_size=0x200)
        hdr = NDSHeader.from_bytes(raw)
        assert hdr.fat_offset == 0x4200
        assert hdr.fat_size == 0x200

    def test_parse_fnt_offset(self):
        raw = _make_nds_header(fnt_offset=0x4000, fnt_size=0x100)
        hdr = NDSHeader.from_bytes(raw)
        assert hdr.fnt_offset == 0x4000
        assert hdr.fnt_size == 0x100

    def test_total_rom_size(self):
        raw = _make_nds_header(total_size=0x800000)
        hdr = NDSHeader.from_bytes(raw)
        assert hdr.total_rom_size == 0x800000

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            NDSHeader.from_bytes(b"\x00" * 100)
