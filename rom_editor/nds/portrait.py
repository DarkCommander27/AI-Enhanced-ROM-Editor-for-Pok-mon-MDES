"""Portrait (kaomado) container and AT4PX decompressor for Explorers of Sky.

kaomado.bin layout
------------------
Offset 0 .. TABLE_BYTES-1 : pointer table
    600 Pokémon × 40 emotions × 4 bytes (uint32 LE) = 96 000 bytes
    A value of 0 means "no portrait for this combination."
    A non-zero value is an absolute byte offset inside kaomado.bin pointing
    to an AT4PX-compressed portrait block.

AT4PX block (header = 19 bytes)
    [0:5]   magic b"AT4PX"
    [5]     reserved (usually 0x00)
    [6:8]   uint16 LE  compressed-data size (not including this header)
    [8:10]  uint16 LE  decompressed size in bytes
    [10:19] 9 look-back distances used by the back-reference compressor

Decompressed portrait (832 bytes)
    [0:32]   16 × uint16 LE BGR555 palette entries
    [32:832] 25 × 8×8-pixel 4bpp NDS tiles (32 bytes each, row-major order)
             Assembled in a 5×5 tile grid → 40×40 pixel image.
"""

from __future__ import annotations

import struct
from typing import Optional

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:  # pragma: no cover
    _HAS_PIL = False

# ---------------------------------------------------------------------------
# kaomado.bin constants
# ---------------------------------------------------------------------------
_DEFAULT_NUM_POKEMON = 600
_NUM_EMOTIONS = 40

_PORTRAIT_BYTES = 800   # expected decompressed tiled 4bpp image size

# ---------------------------------------------------------------------------
# AT4PX decompressor
# ---------------------------------------------------------------------------
_AT4PX_MAGIC = b"AT4PX"
_HDR_SIZE = 18   # 5 + 2 + 9 + 2 (AT4PX)


def _decompress_at4px(data: bytes, offset: int) -> bytes:
    """Decompress one AT4PX block at *offset* inside *data*.

    Raises ``ValueError`` if the magic is missing.
    """
    if data[offset: offset + 5] != _AT4PX_MAGIC:
        raise ValueError(
            f"Expected AT4PX at {offset:#x}, "
            f"got {data[offset: offset + 5]!r}"
        )

    comp_size   = struct.unpack_from("<H", data, offset + 5)[0]
    spec        = data[offset + 7: offset + 16]   # 9 look-back distances
    decomp_size = struct.unpack_from("<H", data, offset + 16)[0]
    comp        = data[offset + _HDR_SIZE: offset + _HDR_SIZE + comp_size]

    output: bytearray = bytearray()
    i = 0
    while len(output) < decomp_size and i < len(comp):
        ctrl = comp[i]
        i += 1
        for bit in range(8):
            if len(output) >= decomp_size or i >= len(comp):
                break
            if not (ctrl & (1 << bit)):
                # Literal byte
                output.append(comp[i])
                i += 1
            else:
                # Back-reference: (key:3 | length-3:5)
                ref      = comp[i]
                i       += 1
                key      = (ref >> 5) & 0x7   # 3-bit index into spec[]
                length   = (ref & 0x1F) + 3   # copy this many bytes
                lookback = spec[key]           # distance back in output
                src      = len(output) - lookback
                for _ in range(length):
                    output.append(output[src] if 0 <= src < len(output) else 0)
                    src += 1

    return bytes(output)


# ---------------------------------------------------------------------------
# Portrait image builder
# ---------------------------------------------------------------------------

def _raw_to_image(raw: bytes, palette_bytes: bytes) -> "Image.Image":
    """Convert decompressed 4bpp tile data + RGB24 palette into a 40×40 image."""
    # Decode 16-color RGB24 palette (48 bytes)
    palette: list[tuple[int, int, int]] = []
    for ci in range(16):
        base = ci * 3
        r = palette_bytes[base]
        g = palette_bytes[base + 1]
        b = palette_bytes[base + 2]
        palette.append((r, g, b))

    # Assemble 5×5 tile grid → 40×40 image
    img = Image.new("RGB", (40, 40))
    px  = img.load()    # type: ignore[assignment]
    tile_data = raw

    for t in range(25):
        tx = (t % 5) * 8
        ty = (t // 5) * 8
        tile = tile_data[t * 32: (t + 1) * 32]
        for row in range(8):
            for col4 in range(4):
                byte = tile[row * 4 + col4]
                # KAO raw portraits use reversed nibble order for left/right pixels.
                px[tx + col4 * 2,     ty + row] = palette[(byte >> 4) & 0xF]
                px[tx + col4 * 2 + 1, ty + row] = palette[byte & 0xF]

    return img


# ---------------------------------------------------------------------------
# Public container
# ---------------------------------------------------------------------------

class PortraitContainer:
    """Wraps kaomado.bin and provides portrait retrieval as PIL Images.

    Usage::

        with open("kaomado.bin", "rb") as f:
            container = PortraitContainer(f.read())

        img = container.get_portrait(25)   # Pikachu's neutral portrait
        if img:
            img.save("pikachu.png")
    """

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._num_emotions = _NUM_EMOTIONS
        self._num_pokemon = self._infer_num_pokemon()
        self._table_entries = self._num_pokemon * self._num_emotions
        self._table_bytes = self._table_entries * 4
        if len(data) < self._table_bytes:
            raise ValueError(
                f"kaomado too short: {len(data)} < {self._table_bytes}"
            )

    def _infer_num_pokemon(self) -> int:
        """Infer ToC size from first positive signed offset in kaomado.kao."""
        for off in range(0, min(len(self._data), 0x100000), 4):
            ptr = struct.unpack_from("<i", self._data, off)[0]
            if ptr > 0:
                entries = ptr // (_NUM_EMOTIONS * 4)
                if entries > 0:
                    return entries
        return _DEFAULT_NUM_POKEMON

    @property
    def num_pokemon(self) -> int:
        return self._num_pokemon

    @property
    def num_emotions(self) -> int:
        return self._num_emotions

    def _ptr(self, poke_idx: int, emotion: int) -> int:
        """Return the file offset for a portrait, or 0 if absent."""
        flat = poke_idx * self._num_emotions + emotion
        if flat >= self._table_entries:
            return 0
        # In kaomado.kao entries are signed; <= 0 means "no portrait".
        val = struct.unpack_from("<i", self._data, flat * 4)[0]
        return val if val > 0 else 0

    def has_portrait(self, poke_idx: int, emotion: int = 0) -> bool:
        """Return ``True`` if a portrait exists for this combination."""
        return self._ptr(poke_idx, emotion) != 0

    def get_portrait(
        self, poke_idx: int, emotion: int = 0
    ) -> Optional["Image.Image"]:
        """Return a 40×40 PIL Image for *poke_idx* / *emotion*, or ``None``."""
        if not _HAS_PIL:
            return None
        if not (0 <= poke_idx < self._num_pokemon):
            return None
        if not (0 <= emotion < self._num_emotions):
            return None
        ptr = self._ptr(poke_idx, emotion)
        if ptr == 0:
            return None
        try:
            # KAO entry = 48-byte RGB24 palette + AT4PX compressed tile data.
            if ptr + 48 >= len(self._data):
                return None
            palette = self._data[ptr: ptr + 48]
            raw = _decompress_at4px(self._data, ptr + 48)
            if len(raw) < _PORTRAIT_BYTES:
                return None
            return _raw_to_image(raw[:_PORTRAIT_BYTES], palette)
        except Exception:
            return None
