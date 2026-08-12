"""Parser for warp data in Pokémon Yellow memory."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from common.enums import MapId, Tileset, WarpActivation
from common.schemas import Coords
from emulator.parsers.map_collision import read_map_collision_tile

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView

_MAP_ID_ADDRESS = 0xD3AB
_TILESET_ID_ADDRESS = 0xD3B4
_MAP_HEIGHT_ADDRESS = 0xD571
_MAP_WIDTH_ADDRESS = 0xD572
_WARP_COUNT_ADDRESS = 0xD3FB
_WARP_ENTRIES_ADDRESS = 0xD3FC
_WARP_RECORD_SIZE = 4

_MAP_HEADER_TABLE_BANK = 0x3F
_MAP_HEADER_POINTERS_ADDRESS = 0x41F2
_MAP_HEADER_BANKS_ADDRESS = 0x43E4
_MAP_HEADER_CONNECTIONS_OFFSET = 9
_MAP_HEADER_SIZE = 10
_MAP_CONNECTION_RECORD_SIZE = 11
_OBJECT_WARP_COUNT_OFFSET = 1
_OBJECT_WARP_ENTRIES_OFFSET = 2


class Warp(BaseModel):
    """An actionable normal warp on the current map."""

    index: int
    coords: Coords
    destination: MapId
    destination_warp_index: int
    destination_coords: Coords | None
    activation: WarpActivation

    model_config = ConfigDict(frozen=True)


def parse_warps(mem: PyBoyMemoryView) -> dict[int, Warp]:
    """Parse actionable normal warps on the current map.

    Each four-byte record remains independent. Records that the current map's
    tiles cannot activate are raw ROM data, not usable warps, and are omitted.

    Args:
        mem: Current PyBoy memory view.

    Returns:
        Actionable warps keyed by their zero-based source-map index.
    """
    map_id = MapId(mem[_MAP_ID_ADDRESS])
    try:
        tileset = Tileset(mem[_TILESET_ID_ADDRESS])
    except ValueError:
        return {}
    warps = {}
    for index in range(mem[_WARP_COUNT_ADDRESS]):
        base = _WARP_ENTRIES_ADDRESS + _WARP_RECORD_SIZE * index
        coords = Coords(row=mem[base], col=mem[base + 1])
        activation = _resolve_activation(
            mem,
            coords,
            map_id=map_id,
            tileset=tileset,
        )
        if activation is None:
            continue
        destination_warp_index = mem[base + 2]
        destination = MapId(mem[base + 3])
        warps[index] = Warp(
            index=index,
            coords=coords,
            destination=destination,
            destination_warp_index=destination_warp_index,
            destination_coords=_resolve_destination_coords(
                mem,
                destination,
                destination_warp_index,
            ),
            activation=activation,
        )
    return warps


def _resolve_destination_coords(
    mem: PyBoyMemoryView,
    destination: MapId,
    destination_warp_index: int,
) -> Coords | None:
    """Resolve an ordinary destination warp record from the loaded ROM."""
    if destination in {MapId.OUTSIDE, MapId.UNKNOWN}:
        return None

    map_id = int(destination)
    map_header_bank = mem[
        _MAP_HEADER_TABLE_BANK,
        _MAP_HEADER_BANKS_ADDRESS + map_id,
    ]
    map_header_pointer_address = _MAP_HEADER_POINTERS_ADDRESS + 2 * map_id
    map_header_address = _read_rom_word(
        mem,
        _MAP_HEADER_TABLE_BANK,
        map_header_pointer_address,
    )

    connection_flags = mem[
        map_header_bank,
        map_header_address + _MAP_HEADER_CONNECTIONS_OFFSET,
    ]
    object_pointer_address = (
        map_header_address
        + _MAP_HEADER_SIZE
        + connection_flags.bit_count() * _MAP_CONNECTION_RECORD_SIZE
    )
    object_address = _read_rom_word(
        mem,
        map_header_bank,
        object_pointer_address,
    )
    warp_count = mem[map_header_bank, object_address + _OBJECT_WARP_COUNT_OFFSET]
    if destination_warp_index >= warp_count:
        return None

    warp_address = (
        object_address + _OBJECT_WARP_ENTRIES_OFFSET + destination_warp_index * _WARP_RECORD_SIZE
    )
    return Coords(
        row=mem[map_header_bank, warp_address],
        col=mem[map_header_bank, warp_address + 1],
    )


def _read_rom_word(mem: PyBoyMemoryView, bank: int, address: int) -> int:
    """Read a little-endian pointer from a specific ROM bank."""
    return mem[bank, address] | mem[bank, address + 1] << 8


def _resolve_activation(
    mem: PyBoyMemoryView,
    coords: Coords,
    *,
    map_id: MapId,
    tileset: Tileset,
) -> WarpActivation | None:
    """Return one working activation input for a warp record."""
    if read_map_collision_tile(mem, coords) in _WARP_TILE_IDS[tileset]:
        return WarpActivation.STEP_ON

    if _uses_map_edge_activation(map_id, tileset):
        height = mem[_MAP_HEIGHT_ADDRESS]
        width = mem[_MAP_WIDTH_ADDRESS]
        return next(
            (
                activation
                for activation, is_outward in (
                    (WarpActivation.UP, coords.row == 0),
                    (WarpActivation.DOWN, coords.row == height - 1),
                    (WarpActivation.LEFT, coords.col == 0),
                    (WarpActivation.RIGHT, coords.col == width - 1),
                )
                if is_outward
            ),
            None,
        )

    for activation, offset in _DIRECTION_OFFSETS.items():
        tile = read_map_collision_tile(mem, coords + offset)
        if _is_directional_warp_tile(tile, activation, map_id):
            return activation
    return None


def _uses_map_edge_activation(map_id: MapId, tileset: Tileset) -> bool:
    """Return whether the ROM selects its outward-map-edge check."""
    if map_id == MapId.SS_ANNE_3F:
        return True
    if map_id in _MAPS_USING_FRONT_TILE_WARP_CHECK:
        return False
    return tileset not in _DIRECTIONAL_WARP_TILESETS


def _is_directional_warp_tile(
    tile: int | None,
    activation: WarpActivation,
    map_id: MapId,
) -> bool:
    """Apply the ordinary or S.S. Anne Bow tile-in-front rule."""
    if map_id == MapId.SS_ANNE_BOW:
        return tile == _SS_ANNE_BOW_WARP_TILE
    return tile in _WARP_CARPET_TILE_IDS[activation]


_DIRECTION_OFFSETS = {
    WarpActivation.UP: (-1, 0),
    WarpActivation.DOWN: (1, 0),
    WarpActivation.LEFT: (0, -1),
    WarpActivation.RIGHT: (0, 1),
}

# ExtraWarpCheck map and tileset exceptions.
_MAPS_USING_FRONT_TILE_WARP_CHECK = {
    MapId.ROCKET_HIDEOUT_B1F,
    MapId.ROCKET_HIDEOUT_B2F,
    MapId.ROCKET_HIDEOUT_B4F,
    MapId.ROCK_TUNNEL_1F,
}
_DIRECTIONAL_WARP_TILESETS = frozenset(
    {
        Tileset.OVERWORLD,
        Tileset.SHIP,
        Tileset.SHIP_PORT,
        Tileset.PLATEAU,
    }
)
_SS_ANNE_BOW_WARP_TILE = 0x15

# data/tilesets/warp_carpet_tile_ids.asm
_WARP_CARPET_TILE_IDS = {
    WarpActivation.DOWN: frozenset({0x01, 0x04, 0x12, 0x17, 0x18, 0x33, 0x3D}),
    WarpActivation.UP: frozenset({0x01, 0x5C}),
    WarpActivation.LEFT: frozenset({0x1A, 0x4B}),
    WarpActivation.RIGHT: frozenset({0x0F, 0x4E}),
}

# data/tilesets/warp_tile_ids.asm, including its intentional fallthroughs.
_WARP_TILE_IDS = {
    Tileset.OVERWORLD: frozenset({0x1B, 0x58}),
    Tileset.REDS_HOUSE_1: frozenset({0x1A, 0x1C}),
    Tileset.MART: frozenset({0x5E}),
    Tileset.FOREST: frozenset({0x3A, 0x5A, 0x5C}),
    Tileset.REDS_HOUSE_2: frozenset({0x1A, 0x1C}),
    Tileset.DOJO: frozenset({0x4A}),
    Tileset.POKECENTER: frozenset({0x5E}),
    Tileset.GYM: frozenset({0x4A}),
    Tileset.HOUSE: frozenset({0x32, 0x54, 0x5C}),
    Tileset.FOREST_GATE: frozenset({0x1A, 0x1C, 0x3B}),
    Tileset.MUSEUM: frozenset({0x1A, 0x1C, 0x3B}),
    Tileset.UNDERGROUND: frozenset({0x13}),
    Tileset.GATE: frozenset({0x1A, 0x1C, 0x3B}),
    Tileset.SHIP: frozenset({0x1E, 0x37, 0x39, 0x4A}),
    Tileset.SHIP_PORT: frozenset(),
    Tileset.CEMETERY: frozenset({0x13, 0x1B}),
    Tileset.INTERIOR: frozenset({0x04, 0x15, 0x55}),
    Tileset.CAVERN: frozenset({0x18, 0x1A, 0x22}),
    Tileset.LOBBY: frozenset({0x1A, 0x1C, 0x38}),
    Tileset.MANSION: frozenset({0x1A, 0x1C, 0x53}),
    Tileset.LAB: frozenset({0x34}),
    Tileset.CLUB: frozenset(),
    Tileset.FACILITY: frozenset({0x13, 0x1B, 0x20, 0x43, 0x58}),
    Tileset.PLATEAU: frozenset({0x1B, 0x3B}),
    Tileset.BEACH_HOUSE: frozenset(),
    Tileset.PLACEHOLDER: frozenset(),
}
