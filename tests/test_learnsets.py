"""Tests for WAZA learnset parsing/writing."""

from __future__ import annotations

import struct

import pytest

from rom_editor.games.explorers_sky.learnsets import WazaLearnsetTable


def _encode_int(value: int) -> bytes:
    if value == 0:
        return b"\x00"
    groups = []
    v = value
    while v > 0:
        groups.append(v & 0x7F)
        v >>= 7
    groups.reverse()
    out = bytearray()
    for i, g in enumerate(groups):
        out.append(g | 0x80 if i < len(groups) - 1 else g)
    return bytes(out)


def _encode_list(values: list[int]) -> bytes:
    out = bytearray()
    for v in values:
        out.extend(_encode_int(v))
    out.append(0)
    return bytes(out)


def _build_sample_waza() -> bytes:
    blob = bytearray(b"\x00" * 256)

    # SIR0 header
    struct.pack_into("<4sIII", blob, 0, b"SIR0", 0x80, 0xC0, 0)
    # WAZA subheader: ptrMovesData, ptrPLSTbl
    struct.pack_into("<II", blob, 0x80, 0x70, 0xA0)

    e1_lvl = _encode_list([10, 5, 20, 9])
    e1_tm = _encode_list([33, 44])
    e1_egg = _encode_list([77])

    e2_lvl = _encode_list([8, 1])
    e2_tm = _encode_list([])
    e2_egg = _encode_list([])

    p = 0x10
    p1 = p
    blob[p:p + len(e1_lvl)] = e1_lvl
    p += len(e1_lvl)
    p2 = p
    blob[p:p + len(e1_tm)] = e1_tm
    p += len(e1_tm)
    p3 = p
    blob[p:p + len(e1_egg)] = e1_egg
    p += len(e1_egg)

    q1 = p
    blob[p:p + len(e2_lvl)] = e2_lvl
    p += len(e2_lvl)
    q2 = p
    blob[p:p + len(e2_tm)] = e2_tm
    p += len(e2_tm)
    q3 = p
    blob[p:p + len(e2_egg)] = e2_egg
    p += len(e2_egg)

    # Pointer table at 0xA0
    struct.pack_into("<III", blob, 0xA0 + 0, 0, 0, 0)
    struct.pack_into("<III", blob, 0xA0 + 12, p1, p2, p3)
    struct.pack_into("<III", blob, 0xA0 + 24, q1, q2, q3)
    # Sentinel invalid pointer to stop parser
    struct.pack_into("<III", blob, 0xA0 + 36, 0xA0, 0, 0)

    return bytes(blob)


def test_parse_learnsets_basic():
    data = _build_sample_waza()
    table = WazaLearnsetTable.from_bytes(data)

    assert len(table) >= 3
    assert table[1].level_up == [(10, 5), (20, 9)]
    assert table[1].tmhm == [33, 44]
    assert table[1].egg == [77]


def test_learnset_roundtrip_same_size_change():
    data = _build_sample_waza()
    table = WazaLearnsetTable.from_bytes(data)

    table[1].level_up[0] = (11, 5)
    out = table.to_bytes()
    table2 = WazaLearnsetTable.from_bytes(out)
    assert table2[1].level_up[0] == (11, 5)


def test_learnset_rejects_size_change():
    data = _build_sample_waza()
    table = WazaLearnsetTable.from_bytes(data)

    table[1].level_up.append((99, 55))
    with pytest.raises(ValueError):
        table.to_bytes()


def test_learnset_autofit_allows_size_change_and_updates_pointers():
    data = _build_sample_waza()
    table = WazaLearnsetTable.from_bytes(data)

    table[1].level_up.append((99, 55))
    out = table.to_bytes(auto_fit=True)
    reparsed = WazaLearnsetTable.from_bytes(out)
    assert reparsed[1].level_up[-1] == (99, 55)


def test_learnset_autofit_overflow_raises():
    data = _build_sample_waza()
    table = WazaLearnsetTable.from_bytes(data)

    # Force growth beyond available room before ptr table.
    table[1].level_up = [(123456, 100)] * 200
    with pytest.raises(ValueError):
        table.to_bytes(auto_fit=True)
