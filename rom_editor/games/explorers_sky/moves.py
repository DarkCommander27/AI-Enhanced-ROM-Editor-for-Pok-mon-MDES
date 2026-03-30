"""Move data structures for Pokémon Mystery Dungeon: Explorers of Sky.

Each move entry in the ``waza_p.bin`` NARC file is 0x1A (26) bytes:

  Offset  Size  Description
  ------  ----  -----------
  0x00    1     Type (0–17)
  0x01    1     Category (0=Physical, 1=Special, 2=Status)
  0x02    2     Unknown / flags (u16 LE)
  0x04    1     Base Power (0 = variable / N/A)
  0x05    1     Accuracy (0 = always hits)
  0x06    1     PP
  0x07    1     PP (secondary; usually same)
  0x08    1     Target (0=enemy, 1=self, 2=all enemies, 3=all in room, …)
  0x09    1     Range (0=front, 1=2-tiles, 2=room, …)
  0x0A    1     Hit count min
  0x0B    1     Hit count max
  0x0C    1     Status condition inflicted
  0x0D    1     Status chance (%)
  0x0E    2     Stat change data (u16 LE)
  0x10    1     AI weight
  0x11    9     Reserved / padding

Source: community research at
  https://projectpokemon.org/home/forums/topic/62264/
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

from rom_editor.nds.narc import NARC
from rom_editor.games.explorers_sky.constants import (
    MOVE_NAMES, TYPE_NAMES, MOVE_CATEGORIES,
)

_ENTRY_SIZE = 0x1A  # 26 bytes
_STRUCT = struct.Struct("<BBHBBBBBBBBBBHBxxxxxxxxx")  # 26 bytes (9 reserved at end)


@dataclass
class MoveEntry:
    """Mutable representation of a single move's data."""

    index: int

    type_id: int         # 0–17
    category: int        # 0=Physical, 1=Special, 2=Status
    flags: int           # raw u16 flags
    base_power: int      # 0 = N/A or variable
    accuracy: int        # 0 = always hits
    pp: int              # PP (primary)
    pp2: int             # PP (secondary / appears identical in practice)
    target: int          # target code
    range_type: int      # range code
    hits_min: int        # minimum hits for multi-hit moves
    hits_max: int        # maximum hits for multi-hit moves
    status_id: int       # status effect inflicted (0 = none)
    status_chance: int   # % chance of status (0 = guaranteed when applied)
    stat_change: int     # packed stat-change data
    ai_weight: int       # relative weight for AI move selection

    @property
    def name(self) -> str:
        if 0 <= self.index < len(MOVE_NAMES):
            return MOVE_NAMES[self.index]
        return f"Move#{self.index}"

    @property
    def type_name(self) -> str:
        return TYPE_NAMES[self.type_id] if 0 <= self.type_id < len(TYPE_NAMES) else "???"

    @property
    def category_name(self) -> str:
        return (
            MOVE_CATEGORIES[self.category]
            if 0 <= self.category < len(MOVE_CATEGORIES) else "???"
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_bytes(self) -> bytes:
        return _STRUCT.pack(
            self.type_id, self.category, self.flags,
            self.base_power, self.accuracy,
            self.pp, self.pp2,
            self.target, self.range_type,
            self.hits_min, self.hits_max,
            self.status_id, self.status_chance,
            self.stat_change, self.ai_weight,
        )

    @classmethod
    def from_bytes(cls, index: int, data: bytes) -> "MoveEntry":
        if len(data) < _ENTRY_SIZE:
            raise ValueError(f"Move data too short: {len(data)} < {_ENTRY_SIZE}")
        (
            type_id, category, flags,
            power, acc, pp, pp2,
            target, range_type,
            hits_min, hits_max,
            status_id, status_chance,
            stat_change, ai_weight,
        ) = _STRUCT.unpack_from(data, 0)
        return cls(
            index=index,
            type_id=type_id, category=category, flags=flags,
            base_power=power, accuracy=acc,
            pp=pp, pp2=pp2,
            target=target, range_type=range_type,
            hits_min=hits_min, hits_max=hits_max,
            status_id=status_id, status_chance=status_chance,
            stat_change=stat_change, ai_weight=ai_weight,
        )

    def __repr__(self) -> str:
        return (
            f"MoveEntry(#{self.index} {self.name!r}, "
            f"type={self.type_name}, cat={self.category_name}, "
            f"pwr={self.base_power}, acc={self.accuracy}, pp={self.pp})"
        )


class MoveTable:
    """Collection of all move entries loaded from the EoS NARC."""

    def __init__(self, entries: list[MoveEntry]) -> None:
        self._entries = entries

    @classmethod
    def from_narc(cls, narc: NARC) -> "MoveTable":
        entries: list[MoveEntry] = []
        for i, narc_file in enumerate(narc):
            if len(narc_file.data) < _ENTRY_SIZE:
                continue
            entry = MoveEntry.from_bytes(i, bytes(narc_file.data))
            entries.append(entry)
        return cls(entries)

    @classmethod
    def from_bytes(cls, data: bytes) -> "MoveTable":
        entries: list[MoveEntry] = []
        num = len(data) // _ENTRY_SIZE
        for i in range(num):
            offset = i * _ENTRY_SIZE
            entry = MoveEntry.from_bytes(i, data[offset:offset + _ENTRY_SIZE])
            entries.append(entry)
        return cls(entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int) -> MoveEntry:
        return self._entries[index]

    def __iter__(self):
        return iter(self._entries)

    def get_by_name(self, name: str) -> Optional[MoveEntry]:
        name_lower = name.lower()
        for e in self._entries:
            if e.name.lower() == name_lower:
                return e
        return None

    def to_bytes(self) -> bytes:
        return b"".join(e.to_bytes() for e in self._entries)

    def write_to_narc(self, narc: NARC) -> None:
        for entry in self._entries:
            if entry.index < narc.num_files:
                narc[entry.index].data = bytearray(entry.to_bytes())
