from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict, computed_field

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from emulator.parsers.utils import INT_TO_CHAR_MAP


class Screen(BaseModel):
    """The state of the screen."""

    top: int
    left: int
    bottom: int
    right: int
    tiles: list[list[int]]  # Each block on screen is a 2x2 square of tiles.
    cursor_index: int

    model_config = ConfigDict(frozen=True)

    @computed_field
    @property
    def is_dialog_box_on_screen(self) -> int:
        """Check if the dialog box is on the screen by checking for the correct corner tiles."""
        top_left, top_right, bottom_left, bottom_right = 121, 123, 125, 126
        return (
            self.tiles[12][0] == top_left
            and self.tiles[12][-1] == top_right
            and self.tiles[17][0] == bottom_left
            and self.tiles[17][-1] == bottom_right
        )

    @computed_field
    @property
    def text(self) -> str:
        """The tiles on screen converted to text if possible."""
        return "\n".join("".join(INT_TO_CHAR_MAP.get(t, " ") for t in row) for row in self.tiles)

    @computed_field
    @property
    def tiles_without_cursor(self) -> list[list[int]]:
        """The tiles on screen without the blinking cursor."""
        cursor = 0xEE
        blank = 0x7F
        return [[t if t != cursor else blank for t in row] for row in self.tiles]


def parse_screen(mem: PyBoyMemoryView) -> Screen:
    """
    Create a new screen state from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the screen state from.
    :return: A new screen state.
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
        cursor_index=mem[0xCC30],
    )
