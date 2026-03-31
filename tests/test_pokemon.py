"""Tests for Pokémon data structures."""

from __future__ import annotations

import struct
import pytest

from rom_editor.games.explorers_sky.pokemon import PokemonEntry, PokemonTable, _ENTRY_SIZE
from rom_editor.games.explorers_sky.constants import POKEMON_NAMES, TYPE_NAMES, ABILITY_NAMES


def _make_pokemon_entry(
    index: int = 1,
    type1: int = 12,   # Grass
    type2: int = 17,   # ??? (no secondary type)
    iq: int = 3,
    ab1: int = 34,     # Overgrow
    ab2: int = 0,
    hp: int = 45, atk: int = 49, spatk: int = 65,
    def_: int = 49, spdef: int = 65, spd: int = 45,
    exp_g: int = 1, exp_y: int = 64,
    rec1: int = 0, size: int = 1, rec2: int = 0,
) -> bytes:
    # Build the 28-byte entry manually using the corrected struct format
    return struct.pack(
        "<BBBBBBHHHHHHBBbBHbxxx",
        type1, type2, iq, ab1, ab2, 0,
        hp, atk, spatk, def_, spdef, spd,
        exp_g, exp_y, rec1, size,
        0,  # pad H
        rec2,  # b (xxx padding bytes auto-added by struct)
    )


class TestPokemonEntry:
    def test_from_bytes_basic(self):
        raw = _make_pokemon_entry(index=1, hp=45, atk=49)
        entry = PokemonEntry.from_bytes(1, raw)
        assert entry.base_hp == 45
        assert entry.base_atk == 49
        assert entry.index == 1

    def test_bst_calculation(self):
        raw = _make_pokemon_entry(hp=45, atk=49, spatk=65, def_=49, spdef=65, spd=45)
        entry = PokemonEntry.from_bytes(1, raw)
        assert entry.bst == 45 + 49 + 65 + 49 + 65 + 45

    def test_name_lookup(self):
        raw = _make_pokemon_entry()
        entry = PokemonEntry.from_bytes(1, raw)
        assert entry.name == "Bulbasaur"

    def test_type_name(self):
        raw = _make_pokemon_entry(type1=0)  # Normal
        entry = PokemonEntry.from_bytes(1, raw)
        assert entry.type1_name == "Normal"

    def test_roundtrip(self):
        raw = _make_pokemon_entry(hp=100, atk=75, spatk=55, def_=80, spdef=60, spd=40)
        entry = PokemonEntry.from_bytes(1, raw)
        repacked = entry.to_bytes()
        entry2 = PokemonEntry.from_bytes(1, repacked)
        assert entry2.base_hp == entry.base_hp
        assert entry2.base_atk == entry.base_atk
        assert entry2.base_spatk == entry.base_spatk
        assert entry2.base_def == entry.base_def
        assert entry2.base_spdef == entry.base_spdef
        assert entry2.base_spd == entry.base_spd

    def test_to_bytes_size(self):
        raw = _make_pokemon_entry()
        entry = PokemonEntry.from_bytes(0, raw)
        assert len(entry.to_bytes()) == _ENTRY_SIZE

    def test_short_data_raises(self):
        with pytest.raises(ValueError):
            PokemonEntry.from_bytes(0, b"\x00" * 4)


class TestPokemonTable:
    def _make_table_bytes(self, count: int = 5) -> bytes:
        return b"".join(
            _make_pokemon_entry(index=i, hp=40 + i)
            for i in range(count)
        )

    def test_from_bytes(self):
        data = self._make_table_bytes(5)
        table = PokemonTable.from_bytes(data)
        assert len(table) == 5

    def test_indexing(self):
        data = self._make_table_bytes(3)
        table = PokemonTable.from_bytes(data)
        assert table[0].index == 0
        assert table[1].index == 1
        assert table[2].index == 2

    def test_get_by_name(self):
        data = self._make_table_bytes(10)
        table = PokemonTable.from_bytes(data)
        # Index 1 = Bulbasaur (if name list loaded correctly)
        entry = table.get_by_name("Bulbasaur")
        if POKEMON_NAMES[1] == "Bulbasaur":
            assert entry is not None
            assert entry.index == 1

    def test_iteration(self):
        data = self._make_table_bytes(3)
        table = PokemonTable.from_bytes(data)
        entries = list(table)
        assert len(entries) == 3

    def test_to_bytes_size(self):
        count = 4
        data = self._make_table_bytes(count)
        table = PokemonTable.from_bytes(data)
        assert len(table.to_bytes()) == count * _ENTRY_SIZE


class TestPokemonTableMdEvolution:
    def _make_md_blob(self) -> bytes:
        entry = bytearray(0x44)
        # Evolution fields
        struct.pack_into("<H", entry, 0x08, 133)   # pre evo
        struct.pack_into("<H", entry, 0x0A, 1)     # LEVEL
        struct.pack_into("<H", entry, 0x0C, 36)    # level param
        struct.pack_into("<H", entry, 0x0E, 0)     # no extra requirement
        # Basic stats fields used by parser
        entry[0x14] = 12   # type1
        entry[0x15] = 17   # type2
        entry[0x17] = 3    # iq group
        entry[0x18] = 34   # ability1
        entry[0x19] = 0    # ability2
        struct.pack_into("<h", entry, 0x1E, 10)    # recruit_rate1
        struct.pack_into("<H", entry, 0x20, 80)    # hp
        struct.pack_into("<h", entry, 0x22, 2)     # recruit_rate2
        entry[0x24] = 82   # atk
        entry[0x25] = 100  # spatk
        entry[0x26] = 83   # def
        entry[0x27] = 100  # spdef
        struct.pack_into("<h", entry, 0x2A, 2)     # size

        return b"MD\x00\x00" + struct.pack("<I", 1) + bytes(entry)

    def test_from_md_parses_evolution_fields(self):
        table = PokemonTable.from_md_bytes(self._make_md_blob())
        e = table[0]
        assert e.pre_evo_index == 133
        assert e.evo_method == 1
        assert e.evo_param1 == 36
        assert e.evo_param2 == 0

    def test_to_md_writes_evolution_fields(self):
        table = PokemonTable.from_md_bytes(self._make_md_blob())
        e = table[0]
        e.pre_evo_index = 2
        e.evo_method = 3
        e.evo_param1 = 77
        e.evo_param2 = 5

        out = table.to_md_bytes()
        base = 8
        assert struct.unpack_from("<H", out, base + 0x08)[0] == 2
        assert struct.unpack_from("<H", out, base + 0x0A)[0] == 3
        assert struct.unpack_from("<H", out, base + 0x0C)[0] == 77
        assert struct.unpack_from("<H", out, base + 0x0E)[0] == 5
