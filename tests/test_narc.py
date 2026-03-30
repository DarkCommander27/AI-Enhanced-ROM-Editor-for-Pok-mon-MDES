"""Tests for the NARC archive handler."""

from __future__ import annotations

import struct
import pytest

from rom_editor.nds.narc import NARC, NARCFile


def _make_minimal_narc(num_files: int = 2, file_size: int = 4) -> bytes:
    """Build a minimal valid NARC with *num_files* files of *file_size* bytes each."""
    # Build file data
    files_data = b""
    fat_entries = []
    for i in range(num_files):
        start = len(files_data)
        content = bytes([i & 0xFF] * file_size)
        files_data += content
        # 4-byte align
        if len(files_data) % 4:
            files_data += b"\xFF" * (4 - len(files_data) % 4)
        end = start + file_size
        fat_entries.append((start, end))

    # BTAF section
    btaf_data = struct.pack("<HH", num_files, 0)
    for start, end in fat_entries:
        btaf_data += struct.pack("<II", start, end)
    btaf_size = 8 + len(btaf_data)
    btaf_section = b"BTAF" + struct.pack("<I", btaf_size) + btaf_data

    # BTNF section (minimal root entry)
    btnf_payload = struct.pack("<IHH", 4, 0, 1)
    btnf_size = 8 + len(btnf_payload)
    btnf_section = b"BTNF" + struct.pack("<I", btnf_size) + btnf_payload

    # GMIF section
    gmif_size = 8 + len(files_data)
    gmif_section = b"GMIF" + struct.pack("<I", gmif_size) + files_data

    # NARC header
    body = btaf_section + btnf_section + gmif_section
    hdr_size = 16
    total_size = hdr_size + len(body)
    narc_header = (
        b"NARC"
        + struct.pack("<HH", 0xFFFE, 0x0100)
        + struct.pack("<IHH", total_size, hdr_size, 3)
    )
    return narc_header + body


class TestNARCParsing:
    def test_parse_valid_narc(self):
        data = _make_minimal_narc(num_files=3, file_size=8)
        narc = NARC.from_bytes(data)
        assert narc.num_files == 3

    def test_file_data_correct(self):
        data = _make_minimal_narc(num_files=4, file_size=4)
        narc = NARC.from_bytes(data)
        for i in range(4):
            assert narc[i].data[0] == i & 0xFF

    def test_invalid_magic_raises(self):
        bad_data = b"XXXX" + b"\x00" * 32
        with pytest.raises(ValueError, match="Not a NARC file"):
            NARC.from_bytes(bad_data)

    def test_len(self):
        data = _make_minimal_narc(num_files=5)
        narc = NARC.from_bytes(data)
        assert len(narc) == 5

    def test_iteration(self):
        data = _make_minimal_narc(num_files=2)
        narc = NARC.from_bytes(data)
        files = list(narc)
        assert len(files) == 2
        assert all(isinstance(f, NARCFile) for f in files)


class TestNARCRoundTrip:
    def test_roundtrip_preserves_data(self):
        data = _make_minimal_narc(num_files=3, file_size=8)
        narc = NARC.from_bytes(data)
        repacked = narc.to_bytes()
        narc2 = NARC.from_bytes(repacked)
        assert narc2.num_files == narc.num_files
        for i in range(narc.num_files):
            assert bytes(narc2[i].data) == bytes(narc[i].data)

    def test_modification_roundtrip(self):
        data = _make_minimal_narc(num_files=2, file_size=4)
        narc = NARC.from_bytes(data)
        narc[0].data = bytearray(b"\xAB\xCD\xEF\x01")
        repacked = narc.to_bytes()
        narc2 = NARC.from_bytes(repacked)
        assert bytes(narc2[0].data) == b"\xAB\xCD\xEF\x01"

    def test_empty_narc(self):
        narc = NARC.empty()
        repacked = narc.to_bytes()
        narc2 = NARC.from_bytes(repacked)
        assert narc2.num_files == 0
