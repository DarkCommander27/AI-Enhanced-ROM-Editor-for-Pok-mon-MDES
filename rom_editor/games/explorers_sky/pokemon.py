"""Pokémon base-stats data structures for Explorers of Sky.

Each Pokémon entry in the ``m_level.bin`` NARC file is 0x1C (28) bytes:

  Offset  Size  Description
  ------  ----  -----------
  0x00    1     Type 1
  0x01    1     Type 2
  0x02    1     IQ Group (0–8)
  0x03    1     Ability 1
  0x04    1     Ability 2
  0x05    1     Flags / bitfield
  0x06    2     Base HP (u16 LE)
  0x08    2     Base ATK (u16 LE)
  0x0A    2     Base SP.ATK (u16 LE)
  0x0C    2     Base DEF (u16 LE)
  0x0E    2     Base SP.DEF (u16 LE)
  0x10    2     Base SPD (u16 LE)
  0x12    1     EXP Group (0–3)
  0x13    1     EXP Yield
  0x14    1     Recruit Rate 1 (signed, 0 = no recruit)
  0x15    1     Size
  0x16    2     Reserved / padding
  0x18    1     Recruit Rate 2
  0x19    3     Reserved / padding

Source: community research at
  https://projectpokemon.org/home/forums/topic/62264/
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

from rom_editor.nds.narc import NARC
from rom_editor.games.explorers_sky.constants import (
    POKEMON_NAMES, TYPE_NAMES, ABILITY_NAMES,
    IQ_GROUP_NAMES, EXP_GROUP_NAMES,
)

_ENTRY_SIZE = 0x1C  # 28 bytes per Pokémon
_STRUCT = struct.Struct("<BBBBBBHHHHHHBBbBHbxxx")  # 28 bytes total


@dataclass
class PokemonEntry:
    """Mutable representation of a single Pokémon's base statistics."""

    index: int          # 0-based position in the NARC

    type1: int          # 0–17
    type2: int          # 0–17
    iq_group: int       # 0–8
    ability1: int       # ability ID
    ability2: int       # ability ID
    flags: int          # raw bitfield byte

    base_hp: int        # 1–255
    base_atk: int       # 1–255
    base_spatk: int     # 1–255
    base_def: int       # 1–255
    base_spdef: int     # 1–255
    base_spd: int       # 1–255

    exp_group: int      # 0–3
    exp_yield: int      # 0–255
    recruit_rate1: int  # signed, 0 = cannot be recruited
    size: int           # body size (1=Tiny … 4=Huge)
    recruit_rate2: int  # secondary recruit flag

    @property
    def name(self) -> str:
        if 0 <= self.index < len(POKEMON_NAMES):
            return POKEMON_NAMES[self.index]
        return f"#{self.index}"

    @property
    def type1_name(self) -> str:
        return TYPE_NAMES[self.type1] if 0 <= self.type1 < len(TYPE_NAMES) else "???"

    @property
    def type2_name(self) -> str:
        return TYPE_NAMES[self.type2] if 0 <= self.type2 < len(TYPE_NAMES) else "???"

    @property
    def ability1_name(self) -> str:
        return (
            ABILITY_NAMES[self.ability1]
            if 0 <= self.ability1 < len(ABILITY_NAMES) else "???"
        )

    @property
    def ability2_name(self) -> str:
        return (
            ABILITY_NAMES[self.ability2]
            if 0 <= self.ability2 < len(ABILITY_NAMES) else "???"
        )

    @property
    def exp_group_name(self) -> str:
        return (
            EXP_GROUP_NAMES[self.exp_group]
            if 0 <= self.exp_group < len(EXP_GROUP_NAMES) else "???"
        )

    @property
    def bst(self) -> int:
        """Base stat total."""
        return (
            self.base_hp + self.base_atk + self.base_spatk
            + self.base_def + self.base_spdef + self.base_spd
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_bytes(self) -> bytes:
        """Pack this entry back to the 28-byte binary format."""
        return _STRUCT.pack(
            self.type1, self.type2, self.iq_group,
            self.ability1, self.ability2, self.flags,
            self.base_hp, self.base_atk, self.base_spatk,
            self.base_def, self.base_spdef, self.base_spd,
            self.exp_group, self.exp_yield,
            self.recruit_rate1, self.size,
            0,  # padding / reserved u16
            self.recruit_rate2,
            # 3 padding bytes handled by 'xxx' in struct format
        )

    @classmethod
    def from_bytes(cls, index: int, data: bytes) -> "PokemonEntry":
        """Parse a 28-byte Pokémon entry."""
        if len(data) < _ENTRY_SIZE:
            raise ValueError(f"Entry data too short: {len(data)} < {_ENTRY_SIZE}")
        (
            type1, type2, iq, ab1, ab2, flags,
            hp, atk, spatk, def_, spdef, spd,
            exp_g, exp_y, rec1, size,
            _pad1, rec2,
        ) = _STRUCT.unpack_from(data, 0)
        return cls(
            index=index,
            type1=type1, type2=type2, iq_group=iq,
            ability1=ab1, ability2=ab2, flags=flags,
            base_hp=hp, base_atk=atk, base_spatk=spatk,
            base_def=def_, base_spdef=spdef, base_spd=spd,
            exp_group=exp_g, exp_yield=exp_y,
            recruit_rate1=rec1, size=size,
            recruit_rate2=rec2,
        )

    def __repr__(self) -> str:
        return (
            f"PokemonEntry(#{self.index} {self.name!r}, "
            f"types=({self.type1_name}/{self.type2_name}), "
            f"BST={self.bst})"
        )


class PokemonTable:
    """Collection of all Pokémon entries loaded from the EoS NARC.

    Usage::

        table = PokemonTable.from_narc(narc)
        entry = table[1]   # Bulbasaur
        entry.base_hp = 55
        raw_narc = table.to_narc_bytes(narc)
    """

    def __init__(self, entries: list[PokemonEntry]) -> None:
        self._entries = entries

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_narc(cls, narc: NARC) -> "PokemonTable":
        """Parse all Pokémon entries from a NARC archive.

        Each file in the NARC corresponds to one Pokémon.  File 0 is the
        "???" placeholder and files 1–493 correspond to National Dex order.
        """
        entries: list[PokemonEntry] = []
        for i, narc_file in enumerate(narc):
            if len(narc_file.data) < _ENTRY_SIZE:
                continue
            entry = PokemonEntry.from_bytes(i, bytes(narc_file.data))
            entries.append(entry)
        return cls(entries)

    @classmethod
    def from_bytes(cls, data: bytes) -> "PokemonTable":
        """Parse entries from a flat byte blob (one entry per 28 bytes)."""
        entries: list[PokemonEntry] = []
        num = len(data) // _ENTRY_SIZE
        for i in range(num):
            offset = i * _ENTRY_SIZE
            entry = PokemonEntry.from_bytes(i, data[offset:offset + _ENTRY_SIZE])
            entries.append(entry)
        return cls(entries)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int) -> PokemonEntry:
        return self._entries[index]

    def __iter__(self):
        return iter(self._entries)

    def get_by_name(self, name: str) -> Optional[PokemonEntry]:
        """Return the first entry whose name matches (case-insensitive)."""
        name_lower = name.lower()
        for e in self._entries:
            if e.name.lower() == name_lower:
                return e
        return None

    def to_bytes(self) -> bytes:
        """Serialize all entries to a flat byte blob."""
        return b"".join(e.to_bytes() for e in self._entries)

    def write_to_narc(self, narc: NARC) -> None:
        """Write modified entries back into their corresponding NARC files."""
        for entry in self._entries:
            if entry.index < narc.num_files:
                narc[entry.index].data = bytearray(entry.to_bytes())
