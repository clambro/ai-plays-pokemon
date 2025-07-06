from enum import IntEnum

from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.enums import MapId


class SpinnerTileIds(BaseModel):
    """
    The tiles that are used for the spinner.

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
    water_tile: int | None
    ledge_tiles_left: list[tuple[int, int]]
    ledge_tiles_right: list[tuple[int, int]]
    ledge_tiles_down: list[tuple[int, int]]
    spinner_tiles: SpinnerTileIds | None
    cut_tree_tiles: tuple[int, int, int, int] | None
    walkable_tiles: list[int]
    collision_pairs: list[frozenset[tuple[int, int]]]
    special_collision_blocks: list[int]
    north_connection: MapId | None
    south_connection: MapId | None
    east_connection: MapId | None
    west_connection: MapId | None

    model_config = ConfigDict(frozen=True)


def parse_map_state(mem: PyBoyMemoryView) -> Map:
    """
    Parse the current map from a snapshot of the memory.

    Tileset values all come from data/tilesets in the decompiled ROM.

    :param mem: The PyBoyMemoryView instance to create the map from.
    :return: A new map.
    """
    tileset_id = _Tileset(mem[0xD3B4])

    if tileset_id == _Tileset.OVERWORLD:
        ledge_tiles_left = [(0x27, 0x2C), (0x27, 0x39)]
        ledge_tiles_right = [(0x2C, 0x0D), (0x2C, 0x1D), (0x1D, 0x24)]
        ledge_tiles_down = [(0x2C, 0x37), (0x39, 0x36), (0x39, 0x37)]
    else:
        ledge_tiles_left = []
        ledge_tiles_right = []
        ledge_tiles_down = []
        cut_tree_tiles = None

    water_tile = 0x14 if tileset_id in [0, 3, 5, 7, 15, 16, 17, 19, 24, 25] else None
    grass_tile = _GRASS_TILE_MAP.get(tileset_id)
    cut_tree_tiles = _CUT_TREE_TILE_MAP.get(tileset_id)

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

    # This is super hacky, but there are some blocks which are not walkable, despite their
    # bottom-left tile being walkable. The reason appears to be the inclusion of one or more of
    # the following tiles, but I can't find anything in the decompiled ROM that explains why.
    special_collision_blocks = _SPECIAL_COLLISION_BLOCKS.get(tileset_id, [])

    return Map(
        id=MapId(mem[0xD3AB]),
        height=mem[0xD571],
        width=mem[0xD572],
        grass_tile=grass_tile,
        water_tile=water_tile,
        ledge_tiles_left=ledge_tiles_left,
        ledge_tiles_right=ledge_tiles_right,
        ledge_tiles_down=ledge_tiles_down,
        cut_tree_tiles=cut_tree_tiles,
        walkable_tiles=walkable_tiles,
        collision_pairs=collision_pairs,
        special_collision_blocks=special_collision_blocks,
        spinner_tiles=_SPINNER_TILE_MAP.get(tileset_id),
        north_connection=MapId(mem[0xD3BE]) if mem[0xD3BE] != terminator else None,
        south_connection=MapId(mem[0xD3C9]) if mem[0xD3C9] != terminator else None,
        east_connection=MapId(mem[0xD3DF]) if mem[0xD3DF] != terminator else None,
        west_connection=MapId(mem[0xD3D4]) if mem[0xD3D4] != terminator else None,
    )


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
    BEACH_HOUSE = 23
    PLATEAU = 24
    BEACH = 25
    PLACEHOLDER = 128  # Required to avoid crashes if you load a saved game, but shouldn't be used.


_GRASS_TILE_MAP = {
    _Tileset.OVERWORLD: 0x52,
    _Tileset.FOREST: 0x20,
    _Tileset.PLATEAU: 0x45,
}

_COLLISION_PAIRS = {
    _Tileset.CAVERN: [
        frozenset([(0x20, 0x05)]),
        frozenset([(0x41, 0x05)]),
        frozenset([(0x2A, 0x05)]),
        frozenset([(0x05, 0x21)]),
        frozenset([(0x14, 0x05)]),
    ],
    _Tileset.FOREST: [
        frozenset([(0x30, 0x2E)]),
        frozenset([(0x52, 0x2E)]),
        frozenset([(0x55, 0x2E)]),
        frozenset([(0x56, 0x2E)]),
        frozenset([(0x20, 0x2E)]),
        frozenset([(0x5E, 0x2E)]),
        frozenset([(0x5F, 0x2E)]),
        frozenset([(0x14, 0x2E)]),
        frozenset([(0x48, 0x2E)]),
    ],
}

_SPECIAL_COLLISION_BLOCKS = {
    _Tileset.CAVERN: [0x10, 0x17, 0x29, 0x31],
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
