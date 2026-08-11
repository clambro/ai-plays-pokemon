"""Parser for map data in Pokémon Yellow memory."""

from enum import IntEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from common.enums import MapId

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView

    from common.schemas import Coords

_OVERWORLD_MAP_ADDRESS = 0xC6E8
_MAP_BORDER_BLOCKS = 3
_TILESET_BANK_ADDRESS = 0xD578
_TILESET_BLOCKS_POINTER_ADDRESS = 0xD579
_MAP_BLOCK_WIDTH_ADDRESS = 0xD3B6
_BLOCK_TILE_WIDTH = 4
_BLOCK_TILE_COUNT = 16
_COLLISION_TILE_ROW_OFFSET = 1
_MAP_CELL_TILE_WIDTH = 2
_CAVERN_BOULDER_BLOCKED_TILES = frozenset({0x15})


class SpinnerTileIds(BaseModel):
    """The tiles that are used for the spinner.

    These are the flattened 4-tile sequences in the order
    [top-left, top-right, bottom-left, bottom-right]
    """

    up: tuple[int, int, int, int]
    down: tuple[int, int, int, int]
    left: tuple[int, int, int, int]
    right: tuple[int, int, int, int]
    stop: tuple[int, int, int, int]


class Map(BaseModel):
    """The state of the current map."""

    id: MapId
    height: int
    width: int
    grass_tile: int | None
    water_tiles: frozenset[int]
    ledge_tiles_left: list[tuple[int, int]]
    ledge_tiles_right: list[tuple[int, int]]
    ledge_tiles_down: list[tuple[int, int]]
    spinner_tiles: SpinnerTileIds | None
    cut_tree_tiles: tuple[int, int, int, int] | None
    boulder_hole_tiles: tuple[int, int, int, int] | None
    pressure_plate_tiles: tuple[int, int, int, int] | None
    pc_tiles: tuple[int, int, int, int] | None
    walkable_tiles: list[int]
    collision_pairs: list[frozenset[int]]
    boulder_blocked_tiles: frozenset[int]
    north_connection: MapId | None
    south_connection: MapId | None
    east_connection: MapId | None
    west_connection: MapId | None

    model_config = ConfigDict(frozen=True)

    def is_boulder_push_terrain_legal(
        self,
        collision_tiles: list[list[int]],
        player_coords: Coords,
        boulder_destination: Coords,
    ) -> bool:
        """Check terrain rules for pushing a boulder two cells from the player."""
        offset = boulder_destination - player_coords
        if (abs(offset.row), abs(offset.col)) not in {(0, 2), (2, 0)}:
            return False

        source_tile = _get_collision_tile_id(collision_tiles, player_coords)
        destination_tile = _get_collision_tile_id(collision_tiles, boulder_destination)
        return (
            source_tile is not None
            and destination_tile is not None
            and destination_tile not in self.boulder_blocked_tiles
            and frozenset((source_tile, destination_tile)) not in self.collision_pairs
        )


def parse_map_state(mem: PyBoyMemoryView) -> Map:
    """Parse the current map from emulator memory.

    Tileset values all come from data/tilesets in the decompiled ROM.

    Args:
        mem: Current PyBoy memory view.

    Returns:
        An immutable snapshot of the current map and its traversal metadata.
    """
    height = mem[0xD571]
    width = mem[0xD572]
    try:
        tileset_id = _Tileset(mem[0xD3B4])
    except ValueError:
        return _unavailable_map(mem)  # Usually means you're on a title screen or between maps.
    if height == 0 or width == 0:
        return _unavailable_map(mem)  # Ditto here.

    if tileset_id == _Tileset.OVERWORLD:
        # These are visual tile pairs within one 2x2 screen cell, not the standing/front tile
        # transitions in data/tilesets/ledge_tiles.asm.
        ledge_tiles_left = [(0x27, 0x2C), (0x27, 0x39)]
        ledge_tiles_right = [(0x0D, 0x24), (0x1D, 0x24)]
        ledge_tiles_down = [(0x2C, 0x37), (0x39, 0x36), (0x39, 0x37)]
    else:
        ledge_tiles_left = []
        ledge_tiles_right = []
        ledge_tiles_down = []
        cut_tree_tiles = None

    water_tiles = _get_water_tiles(tileset_id)
    grass_tile = _GRASS_TILE_MAP.get(tileset_id)
    cut_tree_tiles = _CUT_TREE_TILE_MAP.get(tileset_id)
    boulder_hole_tiles = (0x2F, 0x2F, 0x22, 0x22) if tileset_id == _Tileset.CAVERN else None
    pressure_plate_tiles = (0x2B, 0x2C, 0x2D, 0x2E) if tileset_id == _Tileset.CAVERN else None
    pc_tiles = (0x42, 0x46, 0x52, 0x56) if tileset_id == _Tileset.POKECENTER else None

    walkable_tile_ptr = mem[0xD57D] | (mem[0xD57E] << 8)
    tile_bank, tile_offset = divmod(walkable_tile_ptr, 0x4000)

    walkable_tiles = []
    max_tiles = 0x180
    terminator = 0xFF
    for i in range(max_tiles):
        tile = mem[tile_bank, tile_offset + i]
        if tile == terminator:
            break
        walkable_tiles.append(tile)

    # This is a list of tile pairs that are considered to be colliding, even though both tiles are
    # walkable. It's used to represent elevation differences.
    collision_pairs = _COLLISION_PAIRS.get(tileset_id, [])

    return Map(
        id=MapId(mem[0xD3AB]),
        height=height,
        width=width,
        grass_tile=grass_tile,
        water_tiles=water_tiles,
        ledge_tiles_left=ledge_tiles_left,
        ledge_tiles_right=ledge_tiles_right,
        ledge_tiles_down=ledge_tiles_down,
        cut_tree_tiles=cut_tree_tiles,
        boulder_hole_tiles=boulder_hole_tiles,
        pressure_plate_tiles=pressure_plate_tiles,
        pc_tiles=pc_tiles,
        walkable_tiles=walkable_tiles,
        collision_pairs=collision_pairs,
        boulder_blocked_tiles=(
            _CAVERN_BOULDER_BLOCKED_TILES if tileset_id == _Tileset.CAVERN else frozenset()
        ),
        spinner_tiles=_SPINNER_TILE_MAP.get(tileset_id),
        north_connection=MapId(mem[0xD3BE]) if mem[0xD3BE] != terminator else None,
        south_connection=MapId(mem[0xD3C9]) if mem[0xD3C9] != terminator else None,
        east_connection=MapId(mem[0xD3DF]) if mem[0xD3DF] != terminator else None,
        west_connection=MapId(mem[0xD3D4]) if mem[0xD3D4] != terminator else None,
    )


def _unavailable_map(mem: PyBoyMemoryView) -> Map:
    """Represent startup screens with zero dimensions or non-map data in the tileset byte."""
    return Map(
        id=MapId(mem[0xD3AB]),
        height=0,
        width=0,
        grass_tile=None,
        water_tiles=frozenset(),
        ledge_tiles_left=[],
        ledge_tiles_right=[],
        ledge_tiles_down=[],
        spinner_tiles=None,
        cut_tree_tiles=None,
        boulder_hole_tiles=None,
        pressure_plate_tiles=None,
        pc_tiles=None,
        walkable_tiles=[],
        collision_pairs=[],
        boulder_blocked_tiles=frozenset(),
        north_connection=None,
        south_connection=None,
        east_connection=None,
        west_connection=None,
    )


def parse_map_collision_tiles(mem: PyBoyMemoryView) -> list[list[int]]:
    """Expand the current map's block grid into collision tiles on demand."""
    height = mem[0xD571]
    width = mem[0xD572]
    tileset_bank = mem[_TILESET_BANK_ADDRESS]
    blocks_pointer = mem[_TILESET_BLOCKS_POINTER_ADDRESS] | (
        mem[_TILESET_BLOCKS_POINTER_ADDRESS + 1] << 8
    )
    block_stride = mem[_MAP_BLOCK_WIDTH_ADDRESS] + _MAP_BORDER_BLOCKS * 2

    collision_tiles = []
    for row in range(height):
        collision_row = []
        for col in range(width):
            block_address = (
                _OVERWORLD_MAP_ADDRESS
                + (row // 2 + _MAP_BORDER_BLOCKS) * block_stride
                + col // 2
                + _MAP_BORDER_BLOCKS
            )
            block_id = mem[block_address]
            tile_row = row % 2 * _MAP_CELL_TILE_WIDTH + _COLLISION_TILE_ROW_OFFSET
            tile_col = col % 2 * _MAP_CELL_TILE_WIDTH
            tile_offset = tile_row * _BLOCK_TILE_WIDTH + tile_col
            collision_row.append(
                mem[tileset_bank, blocks_pointer + block_id * _BLOCK_TILE_COUNT + tile_offset]
            )
        collision_tiles.append(collision_row)
    return collision_tiles


def _get_collision_tile_id(collision_tiles: list[list[int]], coords: Coords) -> int | None:
    """Get a collision tile by map coordinate, if the coordinate is in bounds."""
    if (
        coords.row < 0
        or coords.row >= len(collision_tiles)
        or coords.col < 0
        or coords.col >= len(collision_tiles[coords.row])
    ):
        return None
    return collision_tiles[coords.row][coords.col]


class _Tileset(IntEnum):
    """The tileset of the current map."""

    OVERWORLD = 0
    REDS_HOUSE_1 = 1
    MART = 2
    FOREST = 3
    REDS_HOUSE_2 = 4
    DOJO = 5
    POKECENTER = 6
    GYM = 7
    HOUSE = 8
    FOREST_GATE = 9
    MUSEUM = 10
    UNDERGROUND = 11
    GATE = 12
    SHIP = 13
    SHIP_PORT = 14
    CEMETERY = 15
    INTERIOR = 16
    CAVERN = 17
    LOBBY = 18
    MANSION = 19
    LAB = 20
    CLUB = 21
    FACILITY = 22
    PLATEAU = 23
    BEACH_HOUSE = 24
    PLACEHOLDER = 128  # Required to avoid crashes if you load a saved game, but shouldn't be used.


_WATER_TILESETS = {
    _Tileset.OVERWORLD,
    _Tileset.FOREST,
    _Tileset.DOJO,
    _Tileset.GYM,
    _Tileset.SHIP,
    _Tileset.SHIP_PORT,
    _Tileset.CAVERN,
    _Tileset.FACILITY,
    _Tileset.PLATEAU,
}
_WATER_TILE = 0x14
_SHORE_TILES = frozenset({0x48, 0x32})
_WATER_ONLY_TILESETS = {_Tileset.SHIP_PORT, _Tileset.GYM, _Tileset.DOJO}


def _get_water_tiles(tileset_id: _Tileset) -> frozenset[int]:
    """Return lower-left tiles the ROM permits Surf to enter for a tileset."""
    if tileset_id not in _WATER_TILESETS:
        return frozenset()
    if tileset_id in _WATER_ONLY_TILESETS:
        return frozenset({_WATER_TILE})
    return _SHORE_TILES | {_WATER_TILE}


_GRASS_TILE_MAP = {
    _Tileset.OVERWORLD: 0x52,
    _Tileset.FOREST: 0x20,
    _Tileset.PLATEAU: 0x45,
}

_COLLISION_PAIRS = {
    _Tileset.CAVERN: [
        frozenset([0x20, 0x05]),
        frozenset([0x41, 0x05]),
        frozenset([0x2A, 0x05]),
        frozenset([0x05, 0x21]),
        frozenset([0x14, 0x05]),
    ],
    _Tileset.FOREST: [
        frozenset([0x30, 0x2E]),
        frozenset([0x52, 0x2E]),
        frozenset([0x55, 0x2E]),
        frozenset([0x56, 0x2E]),
        frozenset([0x20, 0x2E]),
        frozenset([0x5E, 0x2E]),
        frozenset([0x5F, 0x2E]),
        frozenset([0x14, 0x2E]),
        frozenset([0x48, 0x2E]),
    ],
}

_CUT_TREE_TILE_MAP = {
    _Tileset.OVERWORLD: (0x2D, 0x2E, 0x3D, 0x3E),
    _Tileset.GYM: (0x40, 0x41, 0x50, 0x51),
}

_SPINNER_TILE_MAP = {
    _Tileset.FACILITY: SpinnerTileIds(
        up=(0x21, 0x31, 0x21, 0x31),
        down=(0x20, 0x30, 0x20, 0x30),
        left=(0x21, 0x21, 0x20, 0x20),
        right=(0x31, 0x31, 0x30, 0x30),
        stop=(0x5E, 0x5E, 0x5E, 0x5E),
    ),
    _Tileset.GYM: SpinnerTileIds(
        up=(0x3C, 0x3D, 0x3C, 0x3D),
        down=(0x4C, 0x4D, 0x4C, 0x4D),
        left=(0x3C, 0x3C, 0x4C, 0x4C),
        right=(0x3D, 0x3D, 0x4D, 0x4D),
        stop=(0x3F, 0x3F, 0x3F, 0x3F),
    ),
}
