"""Parser for screen data in Pokémon Yellow memory."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, computed_field

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from common.schemas import Coords
from emulator.parsers.screen_text import decode_screen_tiles

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView


_WINDOW_Y_ADDRESS = 0xFF4A
_SCROLL_Y_ADDRESS = 0xFF42
_SCROLL_X_ADDRESS = 0xFF43
_SCREEN_HEIGHT_PIXELS = 144
_BACKGROUND_MAP_START = 0x9800
_BACKGROUND_MAP_WIDTH = 32
_VRAM_BANK = 0
_TILE_SIZE_PIXELS = 8
_CUT_TREE_COLLISION_TILE = 0x3D


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

    @property
    def naming_screen_name_limit(self) -> int:
        """Get the number of name slots displayed on the naming screen."""
        name_slot_tiles = {0x76, 0x77}
        return sum(tile in name_slot_tiles for tile in self.tiles[3][10:])

    def to_screen_coords(self, map_coords: Coords) -> Coords | None:
        """Convert map coordinates to coordinates within this screen.

        Args:
            map_coords: Coordinates on the current map.

        Returns:
            Coordinates relative to this screen, or ``None`` when the map
            coordinates are outside its viewport.
        """
        if (
            map_coords.row < self.top
            or map_coords.row >= self.bottom
            or map_coords.col < self.left
            or map_coords.col >= self.right
        ):
            return None
        return map_coords - (self.top, self.left)

    def to_map_coords(self, screen_coords: Coords) -> Coords:
        """Convert coordinates within this screen to current-map coordinates.

        Args:
            screen_coords: Coordinates relative to this screen.

        Returns:
            The corresponding coordinates on the current map.
        """
        return Coords(
            row=screen_coords.row + self.top,
            col=screen_coords.col + self.left,
        )


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

    flat_tiles = _resolve_cut_tree_tiles_from_vram(mem, mem[0xC3A0:0xC508])
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


def _resolve_cut_tree_tiles_from_vram(
    mem: PyBoyMemoryView,
    flat_tiles: list[int],
) -> list[int]:
    """Resolve Cut-tree collision tiles using the rendered background map.

    A seamless connected-map transition rebuilds ``wOverworldMap`` from the base map. A later
    map-view update can consequently restore a recently cut tree to ``wTileMap`` while scrolling
    redraws only newly exposed VRAM rows or columns, leaving the passable replacement visible when
    the tree never left the viewport. The ROM handles this exact discrepancy in
    ``GetTileAndCoordsInFrontOfPlayer`` by rereading any ``$3D`` collision tile from VRAM before
    checking movement or Cut. Mirroring that exception keeps parsed terrain consistent with the
    game's own collision decision.
    """
    resolved_tiles = flat_tiles.copy()
    screen_tile_width = SCREEN_WIDTH * 2
    scroll_row = mem[_SCROLL_Y_ADDRESS] // _TILE_SIZE_PIXELS
    scroll_col = mem[_SCROLL_X_ADDRESS] // _TILE_SIZE_PIXELS

    for index, tile in enumerate(flat_tiles):
        if tile != _CUT_TREE_COLLISION_TILE:
            continue

        screen_row, screen_col = divmod(index, screen_tile_width)
        vram_row = (scroll_row + screen_row) % _BACKGROUND_MAP_WIDTH
        vram_col = (scroll_col + screen_col) % _BACKGROUND_MAP_WIDTH
        vram_address = _BACKGROUND_MAP_START + vram_row * _BACKGROUND_MAP_WIDTH + vram_col
        resolved_tiles[index] = mem[_VRAM_BANK, vram_address]

    return resolved_tiles
