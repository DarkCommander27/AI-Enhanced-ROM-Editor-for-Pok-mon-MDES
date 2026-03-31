"""Pokemon learnset parser/writer for WAZA SIR0 files.

Experimental support for level-up, TM/HM, and egg move lists from WAZA files.
The implementation rewrites encoded lists through the learnset pointer table and
keeps writes size-safe by requiring each edited list to keep the same encoded
byte length as the original segment.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass


_SIR0_MAGIC = b"SIR0"
_SIR0_HEADER = struct.Struct("<4sIII")
_WAZA_SUBHEADER = struct.Struct("<II")


@dataclass
class LearnsetEntry:
    index: int
    level_up: list[tuple[int, int]]
    tmhm: list[int]
    egg: list[int]


class WazaLearnsetTable:
    """Editable learnset table backed by a WAZA SIR0 binary blob."""

    def __init__(
        self,
        entries: list[LearnsetEntry],
        blob: bytearray,
        ptr_tbl_offset: int,
        ptr_triples: list[tuple[int, int, int]],
        data_start_offset: int,
    ) -> None:
        self._entries = entries
        self._blob = blob
        self._ptr_tbl_offset = ptr_tbl_offset
        self._ptr_triples = ptr_triples
        self._data_start_offset = data_start_offset

    @staticmethod
    def _decode_one(it: int, data: bytes) -> tuple[int, int]:
        """Decode one integer from PMD integer_encoding varint format."""
        if it >= len(data):
            raise ValueError("Unexpected end while decoding integer")
        first = data[it]
        it += 1
        out = first & 0x7F
        if first & 0x80:
            while True:
                if it >= len(data):
                    raise ValueError("Unexpected end while decoding integer continuation")
                nxt = data[it]
                it += 1
                out = (out << 7) | (nxt & 0x7F)
                if (nxt & 0x80) == 0:
                    break
        return out, it

    @classmethod
    def _decode_list(cls, data: bytes, start: int, hard_end: int) -> tuple[list[int], int]:
        vals: list[int] = []
        i = start
        while i < hard_end:
            if data[i] == 0:
                i += 1
                return vals, i
            val, i = cls._decode_one(i, data)
            vals.append(val)
        raise ValueError("Encoded integer list is not null-terminated")

    @staticmethod
    def _encode_int(value: int) -> bytes:
        if value < 0:
            raise ValueError("Cannot encode negative integer")
        if value == 0:
            return b"\x00"

        groups: list[int] = []
        v = value
        while v > 0:
            groups.append(v & 0x7F)
            v >>= 7
        groups.reverse()

        out = bytearray()
        for i, g in enumerate(groups):
            if i < len(groups) - 1:
                out.append(g | 0x80)
            else:
                out.append(g)
        return bytes(out)

    @classmethod
    def _encode_list(cls, values: list[int]) -> bytes:
        out = bytearray()
        for v in values:
            out.extend(cls._encode_int(v))
        out.append(0)
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "WazaLearnsetTable":
        if len(data) < _SIR0_HEADER.size:
            raise ValueError("WAZA data too short")

        magic, sub_ptr, _ptr_list_ptr, _zero = _SIR0_HEADER.unpack_from(data, 0)
        if magic != _SIR0_MAGIC:
            raise ValueError("Not a SIR0 WAZA file")
        if sub_ptr + _WAZA_SUBHEADER.size > len(data):
            raise ValueError("WAZA subheader out of bounds")

        _ptr_moves_data, ptr_tbl = _WAZA_SUBHEADER.unpack_from(data, sub_ptr)
        if not (0 <= ptr_tbl < len(data)):
            raise ValueError("Learnset pointer table offset is invalid")

        triples: list[tuple[int, int, int]] = []
        off = ptr_tbl
        while off + 12 <= len(data):
            p1, p2, p3 = struct.unpack_from("<III", data, off)
            if any((p != 0 and p >= ptr_tbl) for p in (p1, p2, p3)):
                break
            if not (p1 <= p2 <= p3):
                break
            triples.append((p1, p2, p3))
            off += 12

        if len(triples) < 2:
            raise ValueError("Could not parse WAZA learnset pointer table")

        entries: list[LearnsetEntry] = []
        for idx, (p1, p2, p3) in enumerate(triples):
            next_p1 = triples[idx + 1][0] if idx + 1 < len(triples) else ptr_tbl
            if p1 == p2 == p3 == 0:
                entries.append(LearnsetEntry(index=idx, level_up=[], tmhm=[], egg=[]))
                continue

            if not (0 <= p1 <= p2 <= p3 <= next_p1 <= ptr_tbl):
                raise ValueError(f"Invalid pointer ordering at entry {idx}")

            lvl_vals, lvl_end = cls._decode_list(data, p1, p2)
            tm_vals, tm_end = cls._decode_list(data, p2, p3)
            egg_vals, egg_end = cls._decode_list(data, p3, next_p1)
            if lvl_end > p2 or tm_end > p3 or egg_end > next_p1:
                raise ValueError(f"Learnset segment overflow at entry {idx}")

            if len(lvl_vals) % 2 != 0:
                raise ValueError(f"Level-up list has odd value count at entry {idx}")
            level_up = [(lvl_vals[i], lvl_vals[i + 1]) for i in range(0, len(lvl_vals), 2)]
            entries.append(LearnsetEntry(index=idx, level_up=level_up, tmhm=tm_vals, egg=egg_vals))

        nonzero_ptrs = [p for t in triples for p in t if p > 0]
        data_start = min(nonzero_ptrs) if nonzero_ptrs else ptr_tbl
        return cls(entries, bytearray(data), ptr_tbl, triples, data_start)

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int) -> LearnsetEntry:
        return self._entries[index]

    def __iter__(self):
        return iter(self._entries)

    def to_bytes(self, auto_fit: bool = False) -> bytes:
        if auto_fit:
            return self._to_bytes_autofit()
        return self._to_bytes_same_size()

    def _to_bytes_same_size(self) -> bytes:
        blob = bytearray(self._blob)

        for idx, entry in enumerate(self._entries):
            p1, p2, p3 = self._ptr_triples[idx]
            next_p1 = self._ptr_triples[idx + 1][0] if idx + 1 < len(self._ptr_triples) else self._ptr_tbl_offset

            if p1 == p2 == p3 == 0:
                continue

            old_lvl_len = p2 - p1
            old_tm_len = p3 - p2
            old_egg_len = next_p1 - p3

            flat_lvl: list[int] = []
            for move_id, level in entry.level_up:
                flat_lvl.append(int(move_id))
                flat_lvl.append(int(level))

            new_lvl = self._encode_list(flat_lvl)
            new_tm = self._encode_list([int(v) for v in entry.tmhm])
            new_egg = self._encode_list([int(v) for v in entry.egg])

            if len(new_lvl) != old_lvl_len:
                raise ValueError(
                    f"Entry {idx}: level-up encoding size changed ({len(new_lvl)} != {old_lvl_len})"
                )
            if len(new_tm) != old_tm_len:
                raise ValueError(
                    f"Entry {idx}: TM/HM encoding size changed ({len(new_tm)} != {old_tm_len})"
                )
            if len(new_egg) != old_egg_len:
                raise ValueError(
                    f"Entry {idx}: egg encoding size changed ({len(new_egg)} != {old_egg_len})"
                )

            blob[p1:p2] = new_lvl
            blob[p2:p3] = new_tm
            blob[p3:next_p1] = new_egg

        return bytes(blob)

    def _to_bytes_autofit(self) -> bytes:
        """Repack learnset segments and update pointer-table offsets.

        This mode allows encoded list lengths to change while keeping the
        pointer table location fixed.
        """
        blob = bytearray(self._blob)
        packed = bytearray()
        new_ptrs: list[tuple[int, int, int]] = []

        cursor = self._data_start_offset
        for idx, entry in enumerate(self._entries):
            old_p1, old_p2, old_p3 = self._ptr_triples[idx]
            if old_p1 == old_p2 == old_p3 == 0:
                new_ptrs.append((0, 0, 0))
                continue

            flat_lvl: list[int] = []
            for move_id, level in entry.level_up:
                flat_lvl.append(int(move_id))
                flat_lvl.append(int(level))

            enc_lvl = self._encode_list(flat_lvl)
            enc_tm = self._encode_list([int(v) for v in entry.tmhm])
            enc_egg = self._encode_list([int(v) for v in entry.egg])

            p1 = cursor
            p2 = p1 + len(enc_lvl)
            p3 = p2 + len(enc_tm)
            cursor = p3 + len(enc_egg)

            new_ptrs.append((p1, p2, p3))
            packed.extend(enc_lvl)
            packed.extend(enc_tm)
            packed.extend(enc_egg)

        if cursor > self._ptr_tbl_offset:
            raise ValueError(
                "Auto-fit overflow: repacked learnsets exceed available space "
                f"before pointer table ({cursor} > {self._ptr_tbl_offset})"
            )

        # Fill learnset data area with padding and write packed bytes.
        for i in range(self._data_start_offset, self._ptr_tbl_offset):
            blob[i] = 0xAA
        blob[self._data_start_offset:self._data_start_offset + len(packed)] = packed

        # Rewrite pointer table entries for parsed rows.
        for idx, (p1, p2, p3) in enumerate(new_ptrs):
            struct.pack_into("<III", blob, self._ptr_tbl_offset + idx * 12, p1, p2, p3)

        return bytes(blob)
