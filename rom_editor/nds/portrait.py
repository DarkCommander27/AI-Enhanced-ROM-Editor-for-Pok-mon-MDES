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
from typing import Any, Optional

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    _HAS_PIL = False

try:
    from skytemple_files.graphics.kao.handler import KaoHandler
    _HAS_SKYTEMPLE_KAO = True
except Exception:  # pragma: no cover
    KaoHandler = None  # type: ignore[assignment]
    _HAS_SKYTEMPLE_KAO = False

# ---------------------------------------------------------------------------
# kaomado.bin constants
# ---------------------------------------------------------------------------
_DEFAULT_NUM_POKEMON = 600
_NUM_EMOTIONS = 40

_PORTRAIT_BYTES = 800   # expected decompressed tiled 4bpp image size
_PALETTE_BRG555_BYTES = 32
_PALETTE_RGB24_BYTES = 48

# ---------------------------------------------------------------------------
# AT4PX decompressor
# ---------------------------------------------------------------------------
_AT4PX_MAGIC = b"AT4PX"


def _decompress_at4px_stream(comp: bytes, spec: bytes, decomp_size: int) -> bytes:
    """Decompress one AT4PX compressed payload stream."""
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
                ref = comp[i]
                i += 1
                key = (ref >> 5) & 0x7      # 3-bit index into spec[]
                length = (ref & 0x1F) + 3   # copy this many bytes
                lookback = spec[key]         # distance back in output
                src = len(output) - lookback
                for _ in range(length):
                    if len(output) >= decomp_size:
                        break
                    output.append(output[src] if 0 <= src < len(output) else 0)
                    src += 1

    return bytes(output)


def _decompress_at4px(data: bytes, offset: int) -> bytes:
    """Decompress one AT4PX block at *offset* inside *data*.

    Raises ``ValueError`` if the magic is missing.
    """
    if data[offset: offset + 5] != _AT4PX_MAGIC:
        raise ValueError(
            f"Expected AT4PX at {offset:#x}, "
            f"got {data[offset: offset + 5]!r}"
        )

    # Different dumps/tools expose slightly different AT4PX header layouts.
    # Try known variants and accept the first one that decodes cleanly.
    layouts = [
        # [magic][comp:2][spec:9][decomp:2]
        (18, 5, 7, 16),
        # [magic][reserved:1][comp:2][spec:9][decomp:2]
        (19, 6, 8, 17),
        # [magic][reserved:1][comp:2][decomp:2][spec:9]
        (19, 6, 10, 8),
    ]

    for hdr_size, comp_off, spec_off, decomp_off in layouts:
        try:
            comp_size = struct.unpack_from("<H", data, offset + comp_off)[0]
            decomp_size = struct.unpack_from("<H", data, offset + decomp_off)[0]
            spec = data[offset + spec_off: offset + spec_off + 9]
            if len(spec) != 9 or comp_size <= 0 or decomp_size <= 0:
                continue
            comp_start = offset + hdr_size
            comp_end = comp_start + comp_size
            if comp_end > len(data):
                continue
            out = _decompress_at4px_stream(data[comp_start:comp_end], spec, decomp_size)
            if len(out) >= decomp_size:
                return out[:decomp_size]
        except Exception:
            continue

    raise ValueError(f"Unsupported or corrupted AT4PX block at {offset:#x}")


# ---------------------------------------------------------------------------
# Portrait image builder
# ---------------------------------------------------------------------------

def _palette_from_rgb24(palette_bytes: bytes) -> list[tuple[int, int, int]]:
    """Decode 16-color RGB24 palette (48 bytes)."""
    if len(palette_bytes) < _PALETTE_RGB24_BYTES:
        raise ValueError("RGB24 palette too short")
    palette: list[tuple[int, int, int]] = []
    for ci in range(16):
        base = ci * 3
        palette.append(
            (
                palette_bytes[base],
                palette_bytes[base + 1],
                palette_bytes[base + 2],
            )
        )
    return palette


def _palette_from_bgr555(palette_bytes: bytes) -> list[tuple[int, int, int]]:
    """Decode 16-color Nintendo DS BGR555 palette (32 bytes)."""
    if len(palette_bytes) < _PALETTE_BRG555_BYTES:
        raise ValueError("BGR555 palette too short")
    palette: list[tuple[int, int, int]] = []
    for ci in range(16):
        value = struct.unpack_from("<H", palette_bytes, ci * 2)[0]
        b = (value >> 10) & 0x1F
        g = (value >> 5) & 0x1F
        r = value & 0x1F
        # Expand 5-bit channels to 8-bit.
        palette.append(((r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2)))
    return palette


def _raw_to_image(raw: bytes, palette: list[tuple[int, int, int]]) -> Any:
    """Convert decompressed 4bpp tiles + palette into a 40×40 image."""
    assert Image is not None

    # Assemble 5×5 tile grid → 40×40 image
    img = Image.new("RGB", (40, 40))
    px = img.load()
    assert px is not None
    tile_data = raw

    for t in range(25):
        tx = (t % 5) * 8
        ty = (t // 5) * 8
        tile = tile_data[t * 32: (t + 1) * 32]
        for row in range(8):
            for col4 in range(4):
                byte = tile[row * 4 + col4]
                # NDS 4bpp stores left pixel in low nibble and right pixel in high nibble.
                px[tx + col4 * 2, ty + row] = palette[byte & 0xF]
                px[tx + col4 * 2 + 1, ty + row] = palette[(byte >> 4) & 0xF]

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
        self._kao = None
        self._num_emotions = _NUM_EMOTIONS
        self._num_pokemon = self._infer_num_pokemon()
        self._table_entries = self._num_pokemon * self._num_emotions
        self._table_bytes = self._table_entries * 4
        if len(data) < self._table_bytes:
            raise ValueError(
                f"kaomado too short: {len(data)} < {self._table_bytes}"
            )

        if _HAS_SKYTEMPLE_KAO and KaoHandler is not None:
            try:
                self._kao = KaoHandler.deserialize(data)
                # Prefer SkyTemple model metadata when available.
                self._num_pokemon = int(self._kao.n_entries())
                self._table_entries = self._num_pokemon * self._num_emotions
                self._table_bytes = self._table_entries * 4
            except Exception:
                self._kao = None

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

    def has_precise_decoder(self) -> bool:
        """Return True when SkyTemple-based portrait decoding is available."""
        return self._kao is not None

    def get_portrait(
        self, poke_idx: int, emotion: int = 0
    ) -> Optional[Any]:
        """Return a 40×40 PIL Image for *poke_idx* / *emotion*, or ``None``."""
        if not _HAS_PIL:
            return None

        # Legacy decoding can produce visually incorrect portraits on some ROMs.
        # If SkyTemple decoding is unavailable, prefer no portrait over corrupt output.
        if self._kao is None:
            return None

        # Primary path: use the SkyTemple KAO implementation (accurate format handling).
        if self._kao is not None:
            if not (0 <= poke_idx < self._num_pokemon):
                return None
            if not (0 <= emotion < self._num_emotions):
                return None
            try:
                kao_img = self._kao.get(poke_idx, emotion)
                if kao_img is None:
                    return None
                return kao_img.get().convert("RGBA")
            except Exception:
                # Fall back to legacy decoder below.
                pass

        if not (0 <= poke_idx < self._num_pokemon):
            return None
        if not (0 <= emotion < self._num_emotions):
            return None
        ptr = self._ptr(poke_idx, emotion)
        if ptr == 0:
            return None
        try:
            # Variant A: pointer directly to AT4PX where decompressed payload
            # contains [palette(32) + tile_data(800)].
            if self._data[ptr: ptr + 5] == _AT4PX_MAGIC:
                raw = _decompress_at4px(self._data, ptr)
                if len(raw) >= (_PALETTE_BRG555_BYTES + _PORTRAIT_BYTES):
                    palette = _palette_from_bgr555(raw[:_PALETTE_BRG555_BYTES])
                    return _raw_to_image(
                        raw[_PALETTE_BRG555_BYTES:_PALETTE_BRG555_BYTES + _PORTRAIT_BYTES],
                        palette,
                    )

            # Variant B: [palette(48 RGB24)] + AT4PX(tile_data only).
            at4px_ptr = ptr + _PALETTE_RGB24_BYTES
            if self._data[at4px_ptr: at4px_ptr + 5] == _AT4PX_MAGIC:
                raw = _decompress_at4px(self._data, at4px_ptr)
                if len(raw) >= _PORTRAIT_BYTES:
                    palette = _palette_from_rgb24(self._data[ptr: ptr + _PALETTE_RGB24_BYTES])
                    return _raw_to_image(raw[:_PORTRAIT_BYTES], palette)

            # Variant C: [palette(32 BGR555)] + AT4PX(tile_data only).
            at4px_ptr = ptr + _PALETTE_BRG555_BYTES
            if self._data[at4px_ptr: at4px_ptr + 5] == _AT4PX_MAGIC:
                raw = _decompress_at4px(self._data, at4px_ptr)
                if len(raw) >= _PORTRAIT_BYTES:
                    palette = _palette_from_bgr555(self._data[ptr: ptr + _PALETTE_BRG555_BYTES])
                    return _raw_to_image(raw[:_PORTRAIT_BYTES], palette)

            return None
        except Exception:
            return None
