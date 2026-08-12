"""Tests for the parsed screen viewport."""

import pytest

from common.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from common.schemas import Coords
from emulator.parsers.screen import Screen


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
