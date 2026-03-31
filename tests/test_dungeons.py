"""Tests for dungeon data structures."""

from __future__ import annotations

import struct
import pytest

from rom_editor.games.explorers_sky.dungeons import (
    DungeonEntry, DungeonTable, _HEADER_SIZE,
)
from rom_editor.games.explorers_sky.constants import DUNGEON_NAMES


def _make_dungeon_raw(
    num_floors: int = 12,
    darkness: int = 0,
    weather: int = 0,
    mh_chance: int = 5,
    item_density: int = 5,
    trap_density: int = 5,
    music_id: int = 10,
) -> bytes:
    header = struct.pack(
        "<BBBBBBBBHBBBBBBHBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        num_floors, 0, darkness, weather,
        mh_chance, 0, 0, 0,
        0,             # map_gen_flags
        item_density, trap_density, 5, 0, 0, 0,
        music_id, 0,
    )
    # Pad to _HEADER_SIZE
    header = header[:_HEADER_SIZE].ljust(_HEADER_SIZE, b"\x00")
    return header


class TestDungeonEntry:
    def test_from_bytes_basic(self):
        raw = _make_dungeon_raw(num_floors=15)
        entry = DungeonEntry.from_bytes(0, raw)
        assert entry.num_floors == 15

    def test_darkness_name(self):
        raw = _make_dungeon_raw(darkness=1)
        entry = DungeonEntry.from_bytes(0, raw)
        assert entry.darkness_name == "Semi"

    def test_weather_name(self):
        raw = _make_dungeon_raw(weather=2)
        entry = DungeonEntry.from_bytes(0, raw)
        assert entry.weather_name == "Sandstorm"

    def test_name_lookup(self):
        raw = _make_dungeon_raw()
        entry = DungeonEntry.from_bytes(0, raw)
        expected = DUNGEON_NAMES[0] if DUNGEON_NAMES else f"Dungeon#0"
        assert entry.name == expected

    def test_roundtrip(self):
        raw = _make_dungeon_raw(num_floors=20, item_density=7, trap_density=3)
        entry = DungeonEntry.from_bytes(0, raw)
        repacked = entry.to_bytes(raw)
        entry2 = DungeonEntry.from_bytes(0, repacked)
        assert entry2.num_floors == entry.num_floors
        assert entry2.item_density == entry.item_density
        assert entry2.trap_density == entry.trap_density

    def test_short_data_raises(self):
        with pytest.raises(ValueError):
            DungeonEntry.from_bytes(0, b"\x00" * 4)


class TestDungeonTable:
    def _make_table(self, count: int = 3) -> DungeonTable:
        raws = [_make_dungeon_raw(num_floors=10 + i) for i in range(count)]
        from rom_editor.games.explorers_sky.dungeons import DungeonEntry
        entries = [DungeonEntry.from_bytes(i, raws[i]) for i in range(count)]
        return DungeonTable(entries, raws)

    def test_len(self):
        table = self._make_table(3)
        assert len(table) == 3

    def test_indexing(self):
        table = self._make_table(3)
        assert table[0].num_floors == 10
        assert table[1].num_floors == 11
        assert table[2].num_floors == 12

    def test_iteration(self):
        table = self._make_table(4)
        entries = list(table)
        assert len(entries) == 4

    def test_get_by_name(self):
        table = self._make_table(3)
        name = table[0].name
        entry = table.get_by_name(name)
        assert entry is not None
        assert entry.index == 0

    def test_from_flat_bytes_header_sized_records(self):
        raws = [_make_dungeon_raw(num_floors=20 + i) for i in range(4)]
        blob = b"".join(raws)

        table = DungeonTable.from_flat_bytes(blob, record_size=_HEADER_SIZE)
        assert len(table) == 4
        assert table[0].num_floors == 20
        assert table[3].num_floors == 23

    def test_flat_roundtrip_preserves_record_size(self):
        rec_size = 0x80
        raws = []
        for i in range(3):
            hdr = _make_dungeon_raw(num_floors=30 + i)
            raws.append(hdr + (b"\xAA" * (rec_size - _HEADER_SIZE)))
        blob = b"".join(raws)

        table = DungeonTable.from_flat_bytes(blob, record_size=rec_size)
        table[1].num_floors = 55
        out = table.to_flat_bytes()

        assert len(out) == len(blob)
        reparsed = DungeonTable.from_flat_bytes(out, record_size=rec_size)
        assert reparsed[1].num_floors == 55
