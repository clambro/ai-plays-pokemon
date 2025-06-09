from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH


class Screen(BaseModel):
    """The state of the screen."""

    top: int
    left: int
    bottom: int
    right: int
    tiles: list[list[int]]  # Each block on screen is a 2x2 square of tiles.
    cursor_index: int

    model_config = ConfigDict(frozen=True)


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
