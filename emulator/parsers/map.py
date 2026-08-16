"""Parser for map data in Pokémon Yellow memory."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from common.enums import FacingDirection, MapId, Tileset
from common.schemas import Coords
from emulator.parsers.map_collision import read_map_collision_tile

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView

_CAVERN_BOULDER_BLOCKED_TILES = frozenset({0x15})
_NORTH_CONNECTION_ADDRESS = 0xD3BE
_SOUTH_CONNECTION_ADDRESS = 0xD3C9
_WEST_CONNECTION_ADDRESS = 0xD3D4
_EAST_CONNECTION_ADDRESS = 0xD3DF
_NO_CONNECTION = 0xFF
_NO_TALK_OVER_TILE = 0xFF
_TALK_OVER_TILES_ADDRESS = 0xD57F
_TALK_OVER_TILE_COUNT = 3
_CONNECTION_STRIP_LENGTH_OFFSET = 5
_CONNECTION_Y_ALIGNMENT_OFFSET = 7
_CONNECTION_X_ALIGNMENT_OFFSET = 8
_MAP_BORDER_BLOCKS = 3
_SIGNED_BYTE_START = 0x80
_BYTE_VALUE_COUNT = 0x100


@dataclass(frozen=True, slots=True, kw_only=True)
class MapConnection:
    """A bounded walk-off-map connection and its destination alignment."""

    direction: FacingDirection
    destination_map: MapId
    source_coordinate_start: int
    source_coordinate_end: int
    destination_offset: Coords
    collision_tile_pairs: tuple[tuple[int | None, int | None], ...]

    @property
    def source_coordinates(self) -> range:
        """Return the valid row or column coordinates along the source edge."""
        return range(self.source_coordinate_start, self.source_coordinate_end)

    def get_destination(self, source: Coords) -> Coords:
        """Map a valid source boundary coordinate to the connected map."""
        return source + self.destination_offset

    def get_collision_tile_pair(self, source: Coords) -> tuple[int | None, int | None] | None:
        """Return the standing/front collision tiles for one source coordinate."""
        source_coordinate = (
            source.col
            if self.direction in (FacingDirection.UP, FacingDirection.DOWN)
            else source.row
        )
        if source_coordinate not in self.source_coordinates:
            return None
        return self.collision_tile_pairs[source_coordinate - self.source_coordinate_start]


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
    talk_over_tiles: frozenset[int]
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
    north_connection: MapConnection | None
    south_connection: MapConnection | None
    east_connection: MapConnection | None
    west_connection: MapConnection | None

    model_config = ConfigDict(frozen=True)

    def is_connection_crossable(
        self,
        connection: MapConnection,
        source: Coords,
        *,
        can_surf: bool,
    ) -> bool:
        """Check whether terrain permits moving outward through a map connection.

        The game loads collision tiles from connected maps into a border around the current map.
        Those tiles are available for the entire connection strip regardless of the viewport.

        Args:
            connection: Current-map connection being evaluated.
            source: Reachable coordinate on the current map's edge.
            can_surf: Whether the player can traverse water.

        Returns:
            Whether movement from ``source`` into the connected map is permitted by the loaded
            terrain and collision rules.
        """
        collision_tiles = connection.get_collision_tile_pair(source)
        if collision_tiles is None or None in collision_tiles:
            return False
        source_tile, destination_tile = collision_tiles
        if source_tile is None or destination_tile is None:
            return False

        ledge_tiles = {
            FacingDirection.DOWN: self.ledge_tiles_down,
            FacingDirection.LEFT: self.ledge_tiles_left,
            FacingDirection.RIGHT: self.ledge_tiles_right,
            FacingDirection.UP: [],
        }
        if (source_tile, destination_tile) in ledge_tiles[connection.direction]:
            return True
        if frozenset((source_tile, destination_tile)) in self.collision_pairs:
            return False
        if destination_tile in self.water_tiles:
            return can_surf
        return destination_tile in self.walkable_tiles

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
        tileset_id = Tileset(mem[0xD3B4])
    except ValueError:
        return _unavailable_map(mem)  # Usually means you're on a title screen or between maps.
    if height == 0 or width == 0:
        return _unavailable_map(mem)  # Ditto here.

    if tileset_id == Tileset.OVERWORLD:
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
    talk_over_tiles = frozenset(
        tile
        for tile in mem[_TALK_OVER_TILES_ADDRESS : _TALK_OVER_TILES_ADDRESS + _TALK_OVER_TILE_COUNT]
        if tile != _NO_TALK_OVER_TILE
    )
    grass_tile = _GRASS_TILE_MAP.get(tileset_id)
    cut_tree_tiles = _CUT_TREE_TILE_MAP.get(tileset_id)
    boulder_hole_tiles = (0x2F, 0x2F, 0x22, 0x22) if tileset_id == Tileset.CAVERN else None
    pressure_plate_tiles = (0x2B, 0x2C, 0x2D, 0x2E) if tileset_id == Tileset.CAVERN else None
    pc_tiles = (0x42, 0x46, 0x52, 0x56) if tileset_id == Tileset.POKECENTER else None

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
        talk_over_tiles=talk_over_tiles,
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
            _CAVERN_BOULDER_BLOCKED_TILES if tileset_id == Tileset.CAVERN else frozenset()
        ),
        spinner_tiles=_SPINNER_TILE_MAP.get(tileset_id),
        north_connection=_parse_map_connection(
            mem,
            _NORTH_CONNECTION_ADDRESS,
            FacingDirection.UP,
            height,
            width,
        ),
        south_connection=_parse_map_connection(
            mem,
            _SOUTH_CONNECTION_ADDRESS,
            FacingDirection.DOWN,
            height,
            width,
        ),
        east_connection=_parse_map_connection(
            mem,
            _EAST_CONNECTION_ADDRESS,
            FacingDirection.RIGHT,
            height,
            width,
        ),
        west_connection=_parse_map_connection(
            mem,
            _WEST_CONNECTION_ADDRESS,
            FacingDirection.LEFT,
            height,
            width,
        ),
    )


def _unavailable_map(mem: PyBoyMemoryView) -> Map:
    """Represent startup screens with zero dimensions or non-map data in the tileset byte."""
    return Map(
        id=MapId(mem[0xD3AB]),
        height=0,
        width=0,
        grass_tile=None,
        water_tiles=frozenset(),
        talk_over_tiles=frozenset(),
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


def _parse_map_connection(
    mem: PyBoyMemoryView,
    address: int,
    direction: FacingDirection,
    map_height: int,
    map_width: int,
) -> MapConnection | None:
    """Parse one connection record copied from the current map header."""
    if mem[address] == _NO_CONNECTION:
        return None

    if direction in (FacingDirection.UP, FacingDirection.DOWN):
        source_size = map_width
        alignment = _signed_byte(mem[address + _CONNECTION_X_ALIGNMENT_OFFSET])
        source_row = 0 if direction == FacingDirection.UP else map_height - 1
        destination_offset = Coords(
            row=mem[address + _CONNECTION_Y_ALIGNMENT_OFFSET] - source_row,
            col=alignment,
        )
    else:
        source_size = map_height
        alignment = _signed_byte(mem[address + _CONNECTION_Y_ALIGNMENT_OFFSET])
        source_col = 0 if direction == FacingDirection.LEFT else map_width - 1
        destination_offset = Coords(
            row=alignment,
            col=mem[address + _CONNECTION_X_ALIGNMENT_OFFSET] - source_col,
        )

    source_start, source_end = _get_connection_source_bounds(
        source_size,
        alignment,
        mem[address + _CONNECTION_STRIP_LENGTH_OFFSET],
    )
    return MapConnection(
        direction=direction,
        destination_map=MapId(mem[address]),
        source_coordinate_start=source_start,
        source_coordinate_end=source_end,
        destination_offset=destination_offset,
        collision_tile_pairs=tuple(
            _get_connection_collision_tile_pair(
                mem,
                direction,
                source_coordinate,
                map_height,
                map_width,
            )
            for source_coordinate in range(source_start, source_end)
        ),
    )


def _get_connection_collision_tile_pair(
    mem: PyBoyMemoryView,
    direction: FacingDirection,
    source_coordinate: int,
    map_height: int,
    map_width: int,
) -> tuple[int | None, int | None]:
    """Read the standing/front collision tiles for one connected-map boundary position."""
    if direction in (FacingDirection.UP, FacingDirection.DOWN):
        source = Coords(
            row=0 if direction == FacingDirection.UP else map_height - 1,
            col=source_coordinate,
        )
    else:
        source = Coords(
            row=source_coordinate,
            col=0 if direction == FacingDirection.LEFT else map_width - 1,
        )
    direction_offset = {
        FacingDirection.UP: (-1, 0),
        FacingDirection.DOWN: (1, 0),
        FacingDirection.LEFT: (0, -1),
        FacingDirection.RIGHT: (0, 1),
    }
    destination = source + direction_offset[direction]
    return read_map_collision_tile(mem, source), read_map_collision_tile(mem, destination)


def _get_connection_source_bounds(
    source_size: int,
    alignment: int,
    connection_strip_length: int,
) -> tuple[int, int]:
    """Convert the ROM's block strip and alignment into source tile coordinates."""
    source_block_count = source_size // 2
    connection_offset = -(alignment // 2)
    skipped_destination_blocks = max(-connection_offset - _MAP_BORDER_BLOCKS, 0)
    available_destination_blocks = connection_strip_length + skipped_destination_blocks
    source_start_block = max(connection_offset, 0)

    # The copied strip includes the three-block map border. If it reaches the far side of that
    # border, the current map bounds limit the connection; otherwise the destination map does.
    source_limited_length = source_block_count + _MAP_BORDER_BLOCKS - connection_offset
    if available_destination_blocks < source_limited_length:
        source_end_block = min(
            source_block_count,
            connection_offset + available_destination_blocks,
        )
    else:
        source_end_block = source_block_count

    return source_start_block * 2, source_end_block * 2


def _signed_byte(value: int) -> int:
    """Interpret an unsigned byte as the ROM's signed alignment value."""
    return value - _BYTE_VALUE_COUNT if value >= _SIGNED_BYTE_START else value


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


_WATER_TILESETS = {
    Tileset.OVERWORLD,
    Tileset.FOREST,
    Tileset.DOJO,
    Tileset.GYM,
    Tileset.SHIP,
    Tileset.SHIP_PORT,
    Tileset.CAVERN,
    Tileset.FACILITY,
    Tileset.PLATEAU,
}
_WATER_TILE = 0x14
_SHORE_TILES = frozenset({0x48, 0x32})
_WATER_ONLY_TILESETS = {Tileset.SHIP_PORT, Tileset.GYM, Tileset.DOJO}


def _get_water_tiles(tileset_id: Tileset) -> frozenset[int]:
    """Return lower-left tiles the ROM permits Surf to enter for a tileset."""
    if tileset_id not in _WATER_TILESETS:
        return frozenset()
    if tileset_id in _WATER_ONLY_TILESETS:
        return frozenset({_WATER_TILE})
    return _SHORE_TILES | {_WATER_TILE}


_GRASS_TILE_MAP = {
    Tileset.OVERWORLD: 0x52,
    Tileset.FOREST: 0x20,
    Tileset.PLATEAU: 0x45,
}

_COLLISION_PAIRS = {
    Tileset.CAVERN: [
        frozenset([0x20, 0x05]),
        frozenset([0x41, 0x05]),
        frozenset([0x2A, 0x05]),
        frozenset([0x05, 0x21]),
        frozenset([0x14, 0x05]),
    ],
    Tileset.FOREST: [
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
    Tileset.OVERWORLD: (0x2D, 0x2E, 0x3D, 0x3E),
    Tileset.GYM: (0x40, 0x41, 0x50, 0x51),
}

_SPINNER_TILE_MAP = {
    Tileset.FACILITY: SpinnerTileIds(
        up=(0x21, 0x31, 0x21, 0x31),
        down=(0x20, 0x30, 0x20, 0x30),
        left=(0x21, 0x21, 0x20, 0x20),
        right=(0x31, 0x31, 0x30, 0x30),
        stop=(0x5E, 0x5E, 0x5E, 0x5E),
    ),
    Tileset.GYM: SpinnerTileIds(
        up=(0x3C, 0x3D, 0x3C, 0x3D),
        down=(0x4C, 0x4D, 0x4C, 0x4D),
        left=(0x3C, 0x3C, 0x4C, 0x4C),
        right=(0x3D, 0x3D, 0x4D, 0x4D),
        stop=(0x3F, 0x3F, 0x3F, 0x3F),
    ),
}
