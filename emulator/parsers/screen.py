"""Parser for screen data in Pokémon Yellow memory."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, computed_field

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from emulator.parsers.screen_text import decode_screen_tiles

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView


_WINDOW_Y_ADDRESS = 0xFF4A
_SCREEN_HEIGHT_PIXELS = 144


class Screen(BaseModel):
    """The state of the screen."""

    top: int
    left: int
    bottom: int
    right: int
    tiles: list[list[int]]  # Each block on screen is a 2x2 square of tiles.
    decoded_tiles: list[list[str]]
    is_text_window_visible: bool
    cursor_index: int
    menu_item_index: int
    list_scroll_offset: int

    model_config = ConfigDict(frozen=True)

    @computed_field
    @property
    def is_dialog_box_on_screen(self) -> bool:
        """Check whether the visible text window contains a dialog box."""
        top_left, top_right, bottom_left, bottom_right = 0x79, 0x7B, 0x7D, 0x7E
        horizontal_border = 0x7A
        return (
            self.is_text_window_visible
            and self.tiles[12][0] == top_left
            and self.tiles[12][-1] == top_right
            and self.tiles[17][0] == bottom_left
            and self.tiles[17][-1] == bottom_right
            and all(t == horizontal_border for t in self.tiles[12][1:-1])
            and all(t == horizontal_border for t in self.tiles[17][1:-1])
        )

    @computed_field
    @property
    def text(self) -> str:
        """The rendered text recognized on screen."""
        return "\n".join("".join(row) for row in self.decoded_tiles)

    @computed_field
    @property
    def tiles_without_cursor(self) -> list[list[int]]:
        """The tiles on screen without the blinking cursor."""
        blank = 0x7F
        return [
            [
                blank if glyph == "▼" else tile
                for tile, glyph in zip(tile_row, glyph_row, strict=True)
            ]
            for tile_row, glyph_row in zip(self.tiles, self.decoded_tiles, strict=True)
        ]

    @property
    def naming_screen_name_limit(self) -> int:
        """Get the number of name slots displayed on the naming screen."""
        name_slot_tiles = {0x76, 0x77}
        return sum(tile in name_slot_tiles for tile in self.tiles[3][10:])


def parse_screen(mem: PyBoyMemoryView) -> Screen:
    """Parse the visible screen from emulator memory.

    Args:
        mem: Current PyBoy memory view.

    Returns:
        An immutable snapshot of the screen bounds, tiles, and menu cursors.
    """
    player_y = mem[0xD3AE]
    player_x = mem[0xD3AF]

    top = player_y - PLAYER_OFFSET_Y
    left = player_x - PLAYER_OFFSET_X
    bottom = top + SCREEN_HEIGHT
    right = left + SCREEN_WIDTH

    flat_tiles = mem[0xC3A0:0xC508]
    w = SCREEN_WIDTH * 2  # Convert blocks to 2x2 tiles.
    h = SCREEN_HEIGHT * 2
    tiles = [[flat_tiles[i * w + j] for j in range(w)] for i in range(h)]

    return Screen(
        top=top,
        left=left,
        bottom=bottom,
        right=right,
        tiles=tiles,
        decoded_tiles=decode_screen_tiles(mem, tiles),
        is_text_window_visible=mem[_WINDOW_Y_ADDRESS] < _SCREEN_HEIGHT_PIXELS,
        cursor_index=mem[0xCC30],
        menu_item_index=mem[0xCC26],
        list_scroll_offset=mem[0xCC36],
    )
