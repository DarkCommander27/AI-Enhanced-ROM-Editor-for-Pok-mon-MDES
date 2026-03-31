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
    EVOLUTION_METHOD_NAMES, EVOLUTION_REQUIREMENT_NAMES,
)

_ENTRY_SIZE = 0x1C  # 28 bytes per Pokémon
_STRUCT = struct.Struct("<BBBBBBHHHHHHBBbBHbxxx")  # 28 bytes total

_MD_MAGIC = b"MD\x00\x00"
_MD_HEADER = struct.Struct("<4sI")
_MD_ENTRY_SIZE = 0x44  # 68 bytes per entry in monster.md (EoS)


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
    species_id: int = -1  # raw monster.md entity id (metadata only)

    # Evolution fields (from monster.md, defaults for non-MD sources)
    pre_evo_index: int = 0
    evo_method: int = 0
    evo_param1: int = 0
    evo_param2: int = 0

    @property
    def species_index(self) -> int:
        # For this editor's list and portrait mapping, table index is the stable key.
        return self.index

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
    def evo_method_name(self) -> str:
        return (
            EVOLUTION_METHOD_NAMES[self.evo_method]
            if 0 <= self.evo_method < len(EVOLUTION_METHOD_NAMES) else "Unknown"
        )

    @property
    def evo_requirement_name(self) -> str:
        return (
            EVOLUTION_REQUIREMENT_NAMES[self.evo_param2]
            if 0 <= self.evo_param2 < len(EVOLUTION_REQUIREMENT_NAMES) else "Unknown"
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

    def __init__(self, entries: list[PokemonEntry], source_format: str = "narc") -> None:
        self._entries = entries
        self.source_format = source_format
        self._md_blob: Optional[bytearray] = None
        self._md_count: int = 0

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
        return cls(entries, source_format="narc")

    @classmethod
    def from_md_bytes(cls, data: bytes) -> "PokemonTable":
        """Parse monster.md (MD\0\0 + 68-byte entries) into editable entries.

        The editor focuses on gameplay stats fields, so this maps the core stats/
        type/ability values used by the UI while leaving unknown MD fields untouched
        on write by preserving a private copy of the original blob.
        """
        if len(data) < _MD_HEADER.size:
            raise ValueError("monster.md too short for header")
        magic, count = _MD_HEADER.unpack_from(data, 0)
        if magic != _MD_MAGIC:
            raise ValueError(f"Not monster.md magic: {magic!r}")

        need = _MD_HEADER.size + (count * _MD_ENTRY_SIZE)
        if len(data) < need:
            raise ValueError(
                f"monster.md truncated: {len(data)} < expected {need}"
            )

        entries: list[PokemonEntry] = []
        for i in range(count):
            off = _MD_HEADER.size + i * _MD_ENTRY_SIZE
            chunk = data[off: off + _MD_ENTRY_SIZE]

            # Layout follows ppmd's PokeMonsterData (EoS, 68 bytes).
            species_id = struct.unpack_from("<H", chunk, 0)[0]
            pre_evo_index = struct.unpack_from("<H", chunk, 8)[0]
            evo_method = struct.unpack_from("<H", chunk, 10)[0]
            evo_param1 = struct.unpack_from("<H", chunk, 12)[0]
            evo_param2 = struct.unpack_from("<H", chunk, 14)[0]
            type1 = chunk[20]
            type2 = chunk[21]
            iq_group = chunk[23]
            ability1 = chunk[24]
            ability2 = chunk[25]
            flags = struct.unpack_from("<H", chunk, 26)[0] & 0xFF
            exp_yield = struct.unpack_from("<H", chunk, 28)[0] & 0xFF
            recruit_rate1 = struct.unpack_from("<h", chunk, 30)[0]
            base_hp = struct.unpack_from("<H", chunk, 32)[0]
            recruit_rate2 = struct.unpack_from("<h", chunk, 34)[0]
            base_atk = chunk[36]
            base_spatk = chunk[37]
            base_def = chunk[38]
            base_spdef = chunk[39]
            size = struct.unpack_from("<H", chunk, 42)[0]

            entries.append(PokemonEntry(
                index=i,
                type1=type1,
                type2=type2,
                iq_group=iq_group,
                ability1=ability1,
                ability2=ability2,
                flags=flags,
                base_hp=base_hp,
                base_atk=base_atk,
                base_spatk=base_spatk,
                base_def=base_def,
                base_spdef=base_spdef,
                base_spd=base_spatk,  # MD does not expose separate speed byte here.
                exp_group=0,
                exp_yield=exp_yield,
                recruit_rate1=recruit_rate1,
                size=max(1, min(4, size)),
                recruit_rate2=recruit_rate2,
                species_id=species_id,
                pre_evo_index=pre_evo_index,
                evo_method=evo_method,
                evo_param1=evo_param1,
                evo_param2=evo_param2,
            ))

        table = cls(entries, source_format="md")
        table._md_blob = bytearray(data)
        table._md_count = count
        return table

    @classmethod
    def from_bytes(cls, data: bytes) -> "PokemonTable":
        """Parse entries from a flat byte blob (one entry per 28 bytes)."""
        entries: list[PokemonEntry] = []
        num = len(data) // _ENTRY_SIZE
        for i in range(num):
            offset = i * _ENTRY_SIZE
            entry = PokemonEntry.from_bytes(i, data[offset:offset + _ENTRY_SIZE])
            entries.append(entry)
        return cls(entries, source_format="flat")

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

    def to_md_bytes(self) -> bytes:
        """Serialize edited values back into the original monster.md buffer."""
        if self._md_blob is None:
            raise ValueError("MD source blob unavailable for serialization")

        blob = bytearray(self._md_blob)
        count = self._md_count if self._md_count > 0 else len(self._entries)
        for entry in self._entries:
            if not (0 <= entry.index < count):
                continue
            off = _MD_HEADER.size + entry.index * _MD_ENTRY_SIZE

            struct.pack_into("<H", blob, off + 8, max(0, min(0xFFFF, entry.pre_evo_index)))
            struct.pack_into("<H", blob, off + 10, max(0, min(0xFFFF, entry.evo_method)))
            struct.pack_into("<H", blob, off + 12, max(0, min(0xFFFF, entry.evo_param1)))
            struct.pack_into("<H", blob, off + 14, max(0, min(0xFFFF, entry.evo_param2)))
            blob[off + 20] = max(0, min(255, entry.type1))
            blob[off + 21] = max(0, min(255, entry.type2))
            blob[off + 23] = max(0, min(255, entry.iq_group))
            blob[off + 24] = max(0, min(255, entry.ability1))
            blob[off + 25] = max(0, min(255, entry.ability2))
            struct.pack_into("<H", blob, off + 26, max(0, min(0xFFFF, entry.flags)))
            struct.pack_into("<H", blob, off + 28, max(0, min(0xFFFF, entry.exp_yield)))
            struct.pack_into("<h", blob, off + 30, max(-32768, min(32767, entry.recruit_rate1)))
            struct.pack_into("<H", blob, off + 32, max(1, min(0xFFFF, entry.base_hp)))
            struct.pack_into("<h", blob, off + 34, max(-32768, min(32767, entry.recruit_rate2)))
            blob[off + 36] = max(1, min(255, entry.base_atk))
            blob[off + 37] = max(1, min(255, entry.base_spatk))
            blob[off + 38] = max(1, min(255, entry.base_def))
            blob[off + 39] = max(1, min(255, entry.base_spdef))
            struct.pack_into("<H", blob, off + 42, max(1, min(0xFFFF, entry.size)))

        return bytes(blob)
