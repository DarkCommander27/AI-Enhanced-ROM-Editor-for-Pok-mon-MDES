"""Dungeon data structures for Pokémon Mystery Dungeon: Explorers of Sky.

Each dungeon entry within the ``dungeon.bin`` NARC is a variable-length
structure.  The first 0x60 (96) bytes form the "fixed dungeon header" which
contains the core parameters edited by most tools.

  Offset  Size  Description
  ------  ----  -----------
  0x00    1     Number of floors (B1F is floor 0)
  0x01    1     Unknown
  0x02    1     Darkness level (0=Full, 1=Semi, 2=None)
  0x03    1     Weather (0=Clear, 1=Cloudy, 2=Sandstorm, 3=Fog, …)
  0x04    1     Chance of Monster House (%)
  0x05    1     Chance of buried items (%)
  0x06    1     Chance of empty monster house (%)
  0x07    1     Random starting floor (1 = randomise, 0 = always B1F)
  0x08    2     Map generation flags (u16 LE)
  0x0A    1     Item density
  0x0B    1     Trap density
  0x0C    1     Floor connectivity
  0x0D    1     Water / lava chance (% of floor covered)
  0x0E    1     Kecleon shop chance (%)
  0x0F    1     Unk floor layout
  0x10    2     Music track ID (u16 LE)
  0x12    1     Fixed floor ID (0 = no fixed floor)
  0x13    0x4D  Reserved / additional data

"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional

from rom_editor.nds.narc import NARC
from rom_editor.games.explorers_sky.constants import DUNGEON_NAMES

_HEADER_SIZE = 0x60  # 96 bytes — only the fixed header is edited here
_HEADER_STRUCT = struct.Struct(
    "<"
    "B"   # 0x00 num_floors
    "B"   # 0x01 unk1
    "B"   # 0x02 darkness
    "B"   # 0x03 weather
    "B"   # 0x04 monster_house_chance
    "B"   # 0x05 buried_item_chance
    "B"   # 0x06 empty_mh_chance
    "B"   # 0x07 random_start_floor
    "H"   # 0x08 map_gen_flags
    "B"   # 0x0A item_density
    "B"   # 0x0B trap_density
    "B"   # 0x0C floor_connectivity
    "B"   # 0x0D water_chance
    "B"   # 0x0E kecleon_shop_chance
    "B"   # 0x0F unk_layout
    "H"   # 0x10 music_id
    "B"   # 0x12 fixed_floor_id
    "77s" # 0x13–0x5F reserved
)


@dataclass
class DungeonEntry:
    """Mutable representation of a dungeon's core parameters."""

    index: int

    num_floors: int              # total number of floors
    darkness: int                # 0=Full, 1=Semi, 2=None
    weather: int                 # 0=Clear, 1=Cloudy, 2=Sandstorm, 3=Fog
    monster_house_chance: int    # % chance of a Monster House
    buried_item_chance: int      # % chance of buried items
    empty_mh_chance: int         # % chance of empty Monster House
    random_start_floor: int      # 1 = randomise starting floor
    map_gen_flags: int           # raw generation flags
    item_density: int
    trap_density: int
    floor_connectivity: int
    water_chance: int
    kecleon_shop_chance: int
    music_id: int                # BGM track
    fixed_floor_id: int          # 0 = no fixed floor

    _raw_header: bytes = field(default=b"\x00" * _HEADER_SIZE, repr=False)

    @property
    def name(self) -> str:
        if 0 <= self.index < len(DUNGEON_NAMES):
            return DUNGEON_NAMES[self.index]
        return f"Dungeon#{self.index}"

    @property
    def weather_name(self) -> str:
        names = ["Clear", "Cloudy", "Sandstorm", "Fog", "Snow", "Random"]
        return names[self.weather] if 0 <= self.weather < len(names) else "???"

    @property
    def darkness_name(self) -> str:
        names = ["Full", "Semi", "None"]
        return names[self.darkness] if 0 <= self.darkness < len(names) else "???"

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    @classmethod
    def from_bytes(cls, index: int, data: bytes) -> "DungeonEntry":
        if len(data) < _HEADER_SIZE:
            raise ValueError(f"Dungeon data too short: {len(data)} < {_HEADER_SIZE}")
        (
            num_floors, unk1, darkness, weather,
            mh_chance, buried_chance, empty_mh, rand_start,
            map_flags, item_dens, trap_dens, floor_conn,
            water, kecleon, unk_layout, music, fixed,
            _reserved,
        ) = _HEADER_STRUCT.unpack_from(data, 0)
        return cls(
            index=index,
            num_floors=num_floors,
            darkness=darkness,
            weather=weather,
            monster_house_chance=mh_chance,
            buried_item_chance=buried_chance,
            empty_mh_chance=empty_mh,
            random_start_floor=rand_start,
            map_gen_flags=map_flags,
            item_density=item_dens,
            trap_density=trap_dens,
            floor_connectivity=floor_conn,
            water_chance=water,
            kecleon_shop_chance=kecleon,
            music_id=music,
            fixed_floor_id=fixed,
            _raw_header=bytes(data[:_HEADER_SIZE]),
        )

    def to_bytes(self, full_data: bytes) -> bytes:
        """Return *full_data* with the edited header bytes replaced."""
        new_header = _HEADER_STRUCT.pack(
            self.num_floors, 0,
            self.darkness, self.weather,
            self.monster_house_chance, self.buried_item_chance,
            self.empty_mh_chance, self.random_start_floor,
            self.map_gen_flags,
            self.item_density, self.trap_density, self.floor_connectivity,
            self.water_chance, self.kecleon_shop_chance, 0,
            self.music_id, self.fixed_floor_id,
            self._raw_header[0x13:0x60],  # preserve reserved bytes
        )
        return new_header + full_data[_HEADER_SIZE:]

    def __repr__(self) -> str:
        return (
            f"DungeonEntry(#{self.index} {self.name!r}, "
            f"floors={self.num_floors}, weather={self.weather_name})"
        )


class DungeonTable:
    """Collection of all dungeon entries loaded from the EoS NARC."""

    def __init__(
        self,
        entries: list[DungeonEntry],
        raw_files: list[bytes],
        record_size: Optional[int] = None,
    ) -> None:
        self._entries = entries
        self._raw_files = raw_files
        if record_size is not None:
            self._record_size = record_size
        elif raw_files:
            self._record_size = len(raw_files[0])
        else:
            self._record_size = _HEADER_SIZE

    @classmethod
    def from_narc(cls, narc: NARC) -> "DungeonTable":
        entries: list[DungeonEntry] = []
        raw_files: list[bytes] = []
        for i, narc_file in enumerate(narc):
            raw = bytes(narc_file.data)
            raw_files.append(raw)
            if len(raw) >= _HEADER_SIZE:
                entries.append(DungeonEntry.from_bytes(i, raw))
        return cls(entries, raw_files)

    @classmethod
    def from_flat_bytes(
        cls,
        data: bytes,
        record_size: Optional[int] = None,
    ) -> "DungeonTable":
        """Parse non-NARC dungeon data stored as fixed-size records."""
        if len(data) < _HEADER_SIZE:
            raise ValueError(
                f"Flat dungeon data too short: {len(data)} < {_HEADER_SIZE}"
            )

        rec_size = record_size or cls._infer_record_size(data)
        if rec_size is None:
            raise ValueError(
                "Could not infer non-NARC dungeon record size from DUNGEON.BIN"
            )
        if rec_size < _HEADER_SIZE:
            raise ValueError(
                f"Invalid flat dungeon record size: {rec_size} < {_HEADER_SIZE}"
            )

        count = len(data) // rec_size
        if count == 0:
            raise ValueError("Flat dungeon data has zero records")

        raw_files: list[bytes] = []
        entries: list[DungeonEntry] = []
        for i in range(count):
            off = i * rec_size
            raw = data[off:off + rec_size]
            raw_files.append(raw)
            entries.append(DungeonEntry.from_bytes(i, raw))

        return cls(entries, raw_files, record_size=rec_size)

    @staticmethod
    def _infer_record_size(data: bytes) -> Optional[int]:
        """Infer fixed record size for flat DUNGEON.BIN variants."""
        candidates: list[int] = []

        num_known = len(DUNGEON_NAMES)
        if num_known > 0 and len(data) % num_known == 0:
            guessed = len(data) // num_known
            if guessed >= _HEADER_SIZE:
                candidates.append(guessed)

        for size in (_HEADER_SIZE, 0x80, 0x90, 0xA0, 0xC0, 0x100, 0x120, 0x140):
            if len(data) % size == 0:
                candidates.append(size)

        # Keep order stable while deduplicating.
        uniq: list[int] = []
        for c in candidates:
            if c not in uniq:
                uniq.append(c)
        if not uniq:
            return None

        def score(size: int) -> float:
            count = len(data) // size
            checks = min(count, 24)
            if checks == 0:
                return -1.0
            ok = 0
            for i in range(checks):
                off = i * size
                hdr = data[off:off + _HEADER_SIZE]
                if len(hdr) < _HEADER_SIZE:
                    continue
                try:
                    e = DungeonEntry.from_bytes(i, hdr)
                except Exception:
                    continue
                if 1 <= e.num_floors <= 99:
                    ok += 1
                if 0 <= e.darkness <= 2:
                    ok += 1
                if 0 <= e.weather <= 10:
                    ok += 1
                if 0 <= e.monster_house_chance <= 100:
                    ok += 1
                if 0 <= e.item_density <= 100:
                    ok += 1
                if 0 <= e.trap_density <= 100:
                    ok += 1
            return ok / (checks * 6)

        best = max(uniq, key=score)
        return best

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int) -> DungeonEntry:
        return self._entries[index]

    def __iter__(self):
        return iter(self._entries)

    def get_by_name(self, name: str) -> Optional[DungeonEntry]:
        name_lower = name.lower()
        for e in self._entries:
            if e.name.lower() == name_lower:
                return e
        return None

    def write_to_narc(self, narc: NARC) -> None:
        for entry in self._entries:
            if entry.index < narc.num_files:
                full_raw = self._raw_files[entry.index]
                narc[entry.index].data = bytearray(entry.to_bytes(full_raw))

    def to_flat_bytes(self) -> bytes:
        """Serialize back to fixed-size flat record format."""
        out = bytearray()
        for entry in self._entries:
            if entry.index < len(self._raw_files):
                full_raw = self._raw_files[entry.index]
                out.extend(entry.to_bytes(full_raw))
        return bytes(out)
