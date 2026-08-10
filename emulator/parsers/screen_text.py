"""Decode rendered screen text from the glyphs currently loaded in VRAM."""

from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView


INT_TO_CHAR_MAP = {
    0x6D: ":",  # Tiny colon used by the Pokédex rating screen.
    0x70: "‘",  # noqa: RUF001
    0x71: "’",  # noqa: RUF001
    0x72: "“",
    0x73: "”",
    0x74: "·",
    0x75: "…",
    0x7F: " ",
    0x80: "A",
    0x81: "B",
    0x82: "C",
    0x83: "D",
    0x84: "E",
    0x85: "F",
    0x86: "G",
    0x87: "H",
    0x88: "I",
    0x89: "J",
    0x8A: "K",
    0x8B: "L",
    0x8C: "M",
    0x8D: "N",
    0x8E: "O",
    0x8F: "P",
    0x90: "Q",
    0x91: "R",
    0x92: "S",
    0x93: "T",
    0x94: "U",
    0x95: "V",
    0x96: "W",
    0x97: "X",
    0x98: "Y",
    0x99: "Z",
    0x9A: "(",
    0x9B: ")",
    0x9C: ":",
    0x9D: ";",
    0x9E: "[",
    0x9F: "]",
    0xA0: "a",
    0xA1: "b",
    0xA2: "c",
    0xA3: "d",
    0xA4: "e",
    0xA5: "f",
    0xA6: "g",
    0xA7: "h",
    0xA8: "i",
    0xA9: "j",
    0xAA: "k",
    0xAB: "l",
    0xAC: "m",
    0xAD: "n",
    0xAE: "o",
    0xAF: "p",
    0xB0: "q",
    0xB1: "r",
    0xB2: "s",
    0xB3: "t",
    0xB4: "u",
    0xB5: "v",
    0xB6: "w",
    0xB7: "x",
    0xB8: "y",
    0xB9: "z",
    0xBA: "é",
    0xBB: "'d",
    0xBC: "'l",
    0xBD: "'s",
    0xBE: "'t",
    0xBF: "'v",
    0xE0: "'",
    0xE1: "PK",
    0xE2: "MN",
    0xE3: "-",
    0xE4: "'r",
    0xE5: "'m",
    0xE6: "?",
    0xE7: "!",
    0xE8: ".",
    0xEC: "▷",
    0xED: "▶",
    0xEE: "▼",
    0xEF: "♂",
    0xF0: "¥",
    0xF1: "×",  # noqa: RUF001
    0xF2: ".",
    0xF3: "/",
    0xF4: ",",
    0xF5: "♀",
    0xF6: "0",
    0xF7: "1",
    0xF8: "2",
    0xF9: "3",
    0xFA: "4",
    0xFB: "5",
    0xFC: "6",
    0xFD: "7",
    0xFE: "8",
    0xFF: "9",
}
_NAME_TERMINATOR = 0x50

_LCDC_ADDRESS = 0xFF40
_UNSIGNED_TILE_DATA_FLAG = 1 << 4
_UNSIGNED_TILE_DATA_START = 0x8000
_SIGNED_TILE_DATA_ORIGIN = 0x9000
_VRAM_BANK = 0
_VRAM_TILE_SIZE = 16
_FONT_FIRST_TILE_ID = 0x80
_FONT_LAST_TILE_ID = 0xFF
_TILE_ID_MODULUS = 0x100

_COMMON_GLYPHS_ROM_BANK = 0x04
_COMMON_GLYPHS_START = 0x4600
_COMMON_GLYPHS_END = 0x51C8
_FONT_GRAPHICS = slice(0x0000, 0x0400)
_HP_BAR_AND_STATUS_GRAPHICS = slice(0x0420, 0x0600)
_TEXT_BOX_GRAPHICS = slice(0x08A8, 0x0AA8)
_POKEDEX_GRAPHICS = slice(0x0AA8, 0x0BC8)

_NAMING_GLYPH_ROM_BANK = 0x01
_NAMING_GLYPH_START = 0x65C2
_NAMING_GLYPH_END = 0x65CA
_TOWN_MAP_GLYPH_ROM_BANK = 0x1C
_TOWN_MAP_GLYPH_START = 0x51BE
_TOWN_MAP_GLYPH_END = 0x51C6

_TEXT_BOX_GLYPHS = {
    0x60: "A",
    0x61: "B",
    0x62: "C",
    0x63: "D",
    0x64: "E",
    0x65: "F",
    0x66: "G",
    0x67: "H",
    0x68: "I",
    0x69: "V",
    0x6A: "S",
    0x6B: "L",
    0x6C: "M",
    0x6D: ":",
    0x70: "‘",  # noqa: RUF001
    0x71: "’",  # noqa: RUF001
    0x72: "“",
    0x73: "”",
    0x74: "·",
    0x75: "…",
}
_HP_BAR_AND_STATUS_GLYPHS = {
    0x6E: "Lv",
    0x70: "to",
    0x71: "HP:",
    0x72: "P",
    0x73: "ID",
    0x74: "№",
}
_POKEDEX_GLYPHS = {
    0x60: "′",  # noqa: RUF001
    0x61: "″",
}


def get_text_from_byte_array(arr: list[int]) -> str:
    """Decode a stored name from the game's text encoding."""
    name_chars = []
    for letter in arr:
        if letter == _NAME_TERMINATOR:
            break
        name_chars.append(INT_TO_CHAR_MAP.get(letter, ""))
    return "".join(name_chars).strip()


def decode_screen_tiles(
    mem: PyBoyMemoryView,
    tiles: list[list[int]],
) -> list[list[str]]:
    """Decode tile IDs using the glyph patterns currently loaded in VRAM.

    Background tile IDs are mutable slots rather than stable character codes. A tile is therefore
    text only when its current VRAM pattern matches a semantic glyph from the game's graphics.

    Args:
        mem: Current PyBoy memory view.
        tiles: Visible background tile IDs.

    Returns:
        A grid of decoded glyphs parallel to ``tiles``. Non-text tiles are spaces.
    """
    try:
        glyph_catalog = _get_glyph_catalog(mem)
        lcdc = mem[_LCDC_ADDRESS]
        decoded_by_tile_id: dict[int, str] = {}
        for tile_id in {tile for row in tiles for tile in row} & glyph_catalog.keys():
            address = _get_vram_tile_address(tile_id, lcdc)
            pattern = bytes(mem[_VRAM_BANK, address : address + _VRAM_TILE_SIZE])
            decoded_by_tile_id[tile_id] = glyph_catalog[tile_id].get(pattern, " ")
        return [[decoded_by_tile_id.get(tile, " ") for tile in row] for row in tiles]
    except Exception:  # noqa: BLE001
        # Text recognition is auxiliary. An incompatible ROM must not prevent state parsing.
        return [[" " for _ in row] for row in tiles]


def _get_vram_tile_address(tile_id: int, lcdc: int) -> int:
    """Resolve a background tile ID to its bank-zero VRAM pattern address."""
    if lcdc & _UNSIGNED_TILE_DATA_FLAG:
        return _UNSIGNED_TILE_DATA_START + tile_id * _VRAM_TILE_SIZE
    signed_tile_id = tile_id if tile_id < _FONT_FIRST_TILE_ID else tile_id - _TILE_ID_MODULUS
    return _SIGNED_TILE_DATA_ORIGIN + signed_tile_id * _VRAM_TILE_SIZE


def _get_glyph_catalog(mem: PyBoyMemoryView) -> dict[int, dict[bytes, str]]:
    """Get a cached glyph catalog sourced from the ROM being emulated."""
    common_graphics = bytes(
        mem[
            _COMMON_GLYPHS_ROM_BANK,
            _COMMON_GLYPHS_START:_COMMON_GLYPHS_END,
        ]
    )
    naming_glyph = bytes(mem[_NAMING_GLYPH_ROM_BANK, _NAMING_GLYPH_START:_NAMING_GLYPH_END])
    town_map_glyph = bytes(mem[_TOWN_MAP_GLYPH_ROM_BANK, _TOWN_MAP_GLYPH_START:_TOWN_MAP_GLYPH_END])
    return _build_glyph_catalog(common_graphics, naming_glyph, town_map_glyph)


@cache
def _build_glyph_catalog(
    common_graphics: bytes,
    naming_glyph: bytes,
    town_map_glyph: bytes,
) -> dict[int, dict[bytes, str]]:
    """Build the rendered-glyph catalog from graphics stored in the active ROM."""
    catalog: dict[int, dict[bytes, str]] = {}

    font_glyphs = {
        tile_id: glyph
        for tile_id, glyph in INT_TO_CHAR_MAP.items()
        if _FONT_FIRST_TILE_ID <= tile_id <= _FONT_LAST_TILE_ID
    }
    _register_glyph_sheet(
        catalog,
        common_graphics[_FONT_GRAPHICS],
        first_tile_id=_FONT_FIRST_TILE_ID,
        glyphs=font_glyphs,
        bits_per_pixel=1,
    )
    _register_glyph_sheet(
        catalog,
        common_graphics[_TEXT_BOX_GRAPHICS],
        first_tile_id=0x60,
        glyphs=_TEXT_BOX_GLYPHS,
        bits_per_pixel=2,
    )
    _register_glyph_sheet(
        catalog,
        common_graphics[_HP_BAR_AND_STATUS_GRAPHICS],
        first_tile_id=0x62,
        glyphs=_HP_BAR_AND_STATUS_GLYPHS,
        bits_per_pixel=2,
    )
    _register_glyph_sheet(
        catalog,
        common_graphics[_POKEDEX_GRAPHICS],
        first_tile_id=0x60,
        glyphs=_POKEDEX_GLYPHS,
        bits_per_pixel=2,
    )
    _register_glyph_sheet(
        catalog,
        town_map_glyph,
        first_tile_id=0xED,
        glyphs={0xED: "▲"},
        bits_per_pixel=1,
    )
    _register_glyph_sheet(
        catalog,
        naming_glyph,
        first_tile_id=0xF0,
        glyphs={0xF0: "ED"},
        bits_per_pixel=1,
    )
    return catalog


def _register_glyph_sheet(
    catalog: dict[int, dict[bytes, str]],
    data: bytes,
    *,
    first_tile_id: int,
    glyphs: dict[int, str],
    bits_per_pixel: int,
) -> None:
    """Register semantic glyphs from one canonical graphics sheet."""
    patterns = _read_tile_patterns(data, bits_per_pixel=bits_per_pixel)
    for tile_id, glyph in glyphs.items():
        pattern_index = tile_id - first_tile_id
        if pattern_index < 0 or pattern_index >= len(patterns):
            continue

        pattern = patterns[pattern_index]
        glyphs_by_pattern = catalog.setdefault(tile_id, {})
        existing_glyph = glyphs_by_pattern.get(pattern)
        if existing_glyph is not None and existing_glyph != glyph:
            glyphs_by_pattern[pattern] = " "
        else:
            glyphs_by_pattern[pattern] = glyph


def _read_tile_patterns(
    data: bytes,
    *,
    bits_per_pixel: int,
) -> tuple[bytes, ...]:
    """Read graphics tiles and normalize them to the two-bit VRAM representation."""
    if bits_per_pixel not in {1, 2}:
        return ()
    bytes_per_source_tile = 8 * bits_per_pixel
    if len(data) % bytes_per_source_tile:
        return ()

    patterns = []
    for offset in range(0, len(data), bytes_per_source_tile):
        source = data[offset : offset + bytes_per_source_tile]
        if bits_per_pixel == 1:
            source = bytes(byte for row in source for byte in (row, row))
        patterns.append(source)
    return tuple(patterns)
