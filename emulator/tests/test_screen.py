"""Tests for the parsed screen viewport."""

from unittest.mock import MagicMock, patch

import pytest

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from common.schemas import Coords
from emulator.parsers.screen import Screen, parse_screen


def test_parse_screen_uses_vram_for_cut_tree_collision_tile() -> None:
    """Keep parsed Cut-tree terrain consistent with the game's collision source."""
    tile_height = SCREEN_HEIGHT * 2
    tile_width = SCREEN_WIDTH * 2
    screen_row = 11
    screen_col = 8
    wram_tree_tile = 0x3D
    vram_replacement_tile = 0x0B
    wram_tiles = [0] * (tile_height * tile_width)
    wram_tiles[screen_row * tile_width + screen_col] = wram_tree_tile

    scroll_row = 29
    scroll_col = 30
    vram_row = (scroll_row + screen_row) % 32
    vram_col = (scroll_col + screen_col) % 32
    vram_address = 0x9800 + vram_row * 32 + vram_col
    register_values = {
        0xD3AE: PLAYER_OFFSET_Y,
        0xD3AF: PLAYER_OFFSET_X,
        0xFF42: scroll_row * 8,
        0xFF43: scroll_col * 8,
        0xFF4A: 144,
        0xCC30: 0,
        0xCC26: 0,
        0xCC36: 0,
    }
    mem = MagicMock()

    def read_memory(address: int | slice | tuple[int, int]) -> int | list[int]:
        if isinstance(address, slice):
            assert address == slice(0xC3A0, 0xC508)
            return wram_tiles
        if isinstance(address, tuple):
            assert address == (0, vram_address)
            return vram_replacement_tile
        return register_values[address]

    mem.__getitem__.side_effect = read_memory
    decoded_tiles = [[""] * tile_width for _ in range(tile_height)]

    with patch("emulator.parsers.screen.decode_screen_tiles", return_value=decoded_tiles):
        screen = parse_screen(mem)

    assert wram_tiles[screen_row * tile_width + screen_col] == wram_tree_tile
    assert screen.tiles[screen_row][screen_col] == vram_replacement_tile


@pytest.mark.parametrize(
    ("map_coords", "expected"),
    [
        (Coords(row=-2, col=3), Coords(row=0, col=0)),
        (Coords(row=6, col=12), Coords(row=8, col=9)),
        (Coords(row=-3, col=3), None),
        (Coords(row=7, col=3), None),
        (Coords(row=-2, col=2), None),
        (Coords(row=-2, col=13), None),
    ],
)
def test_to_screen_coords(map_coords: Coords, expected: Coords | None) -> None:
    """Map coordinates are translated only when they are inside the viewport."""
    screen = _make_screen(top=-2, left=3)

    assert screen.to_screen_coords(map_coords) == expected


def test_to_map_coords() -> None:
    """Screen coordinates are translated relative to the viewport origin."""
    screen = _make_screen(top=-2, left=3)

    assert screen.to_map_coords(Coords(row=0, col=0)) == Coords(row=-2, col=3)
    assert screen.to_map_coords(Coords(row=8, col=9)) == Coords(row=6, col=12)


def _make_screen(*, top: int, left: int) -> Screen:
    """Create a screen with the specified current-map viewport origin."""
    tile_height = SCREEN_HEIGHT * 2
    tile_width = SCREEN_WIDTH * 2
    return Screen(
        top=top,
        left=left,
        bottom=top + SCREEN_HEIGHT,
        right=left + SCREEN_WIDTH,
        tiles=[[0] * tile_width for _ in range(tile_height)],
        decoded_tiles=[[""] * tile_width for _ in range(tile_height)],
        is_text_window_visible=False,
        cursor_index=0,
        menu_item_index=0,
        list_scroll_offset=0,
    )
