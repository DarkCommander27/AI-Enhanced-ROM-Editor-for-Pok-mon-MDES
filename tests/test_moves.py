"""Tests for move data structures."""

from __future__ import annotations

import struct
import pytest

from rom_editor.games.explorers_sky.moves import MoveEntry, MoveTable, _ENTRY_SIZE
from rom_editor.games.explorers_sky.constants import TYPE_NAMES, MOVE_CATEGORIES, MOVE_NAMES


def _make_move_entry(
    index: int = 1,
    type_id: int = 0,   # Normal
    category: int = 0,  # Physical
    power: int = 40,
    acc: int = 100,
    pp: int = 35,
) -> bytes:
    return struct.pack(
        "<BBHBBBBBBBBBBHBxxxxxxxxx",
        type_id, category, 0,     # type, category, flags
        power, acc, pp, pp,        # power, accuracy, pp, pp2
        0, 0,                      # target, range
        1, 1,                      # hits_min, hits_max
        0, 0,                      # status_id, status_chance
        0, 80,                     # stat_change, ai_weight
        # 9 padding bytes from 'xxxxxxxxx'
    )


class TestMoveEntry:
    def test_from_bytes_basic(self):
        raw = _make_move_entry(index=1, power=40, acc=100, pp=35)
        entry = MoveEntry.from_bytes(1, raw)
        assert entry.base_power == 40
        assert entry.accuracy == 100
        assert entry.pp == 35

    def test_type_name(self):
        raw = _make_move_entry(type_id=1)  # Fire
        entry = MoveEntry.from_bytes(1, raw)
        assert entry.type_name == "Fire"

    def test_category_name(self):
        raw = _make_move_entry(category=1)  # Special
        entry = MoveEntry.from_bytes(1, raw)
        assert entry.category_name == "Special"

    def test_name_lookup(self):
        raw = _make_move_entry()
        entry = MoveEntry.from_bytes(1, raw)
        assert entry.name == MOVE_NAMES[1]

    def test_roundtrip(self):
        raw = _make_move_entry(power=80, acc=90, pp=10)
        entry = MoveEntry.from_bytes(1, raw)
        repacked = entry.to_bytes()
        entry2 = MoveEntry.from_bytes(1, repacked)
        assert entry2.base_power == entry.base_power
        assert entry2.accuracy == entry.accuracy
        assert entry2.pp == entry.pp

    def test_to_bytes_size(self):
        raw = _make_move_entry()
        entry = MoveEntry.from_bytes(0, raw)
        assert len(entry.to_bytes()) == _ENTRY_SIZE

    def test_short_data_raises(self):
        with pytest.raises(ValueError):
            MoveEntry.from_bytes(0, b"\x00" * 4)


class TestMoveTable:
    def _make_table_bytes(self, count: int = 5) -> bytes:
        return b"".join(
            _make_move_entry(index=i, power=min(255, 10 + i * 5))
            for i in range(count)
        )

    def test_from_bytes(self):
        data = self._make_table_bytes(5)
        table = MoveTable.from_bytes(data)
        assert len(table) == 5

    def test_power_values(self):
        data = self._make_table_bytes(3)
        table = MoveTable.from_bytes(data)
        assert table[0].base_power == 10
        assert table[1].base_power == 15
        assert table[2].base_power == 20

    def test_iteration(self):
        data = self._make_table_bytes(4)
        table = MoveTable.from_bytes(data)
        assert list(table) == [table[i] for i in range(4)]

    def test_to_bytes_size(self):
        count = 6
        data = self._make_table_bytes(count)
        table = MoveTable.from_bytes(data)
        assert len(table.to_bytes()) == count * _ENTRY_SIZE

    def test_get_by_name(self):
        data = self._make_table_bytes(10)
        table = MoveTable.from_bytes(data)
        name = MOVE_NAMES[1]
        entry = table.get_by_name(name)
        assert entry is not None
        assert entry.index == 1
