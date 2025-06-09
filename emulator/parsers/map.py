from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.enums import MapId


class Map(BaseModel):
    """The state of the current map."""

    id: MapId
    height: int
    width: int
    grass_tile: int
    water_tile: int
    ledge_tiles: list[int]
    cut_tree_tiles: list[int]
    walkable_tiles: list[int]
    north_connection: MapId | None
    south_connection: MapId | None
    east_connection: MapId | None
    west_connection: MapId | None

    model_config = ConfigDict(frozen=True)


def parse_map_state(mem: PyBoyMemoryView) -> Map:
    """
    Parse the current map from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the map from.
    :return: A new map.
    """
    tileset_id = mem[0xD3B4]

    # These were found by inspection.
    ledge_tiles = [54, 55] if tileset_id == 0 else []
    cut_tree_tiles = [45, 46, 61, 62] if tileset_id == 0 else []

    walkable_tile_ptr = mem[0xD57D] | (mem[0xD57E] << 8)
    walkable_tiles = []

    max_tiles = 0x180
    terminator = 0xFF
    for i in range(max_tiles):
        if mem[walkable_tile_ptr + i] == terminator:
            break
        walkable_tiles.append(mem[walkable_tile_ptr + i])

    return Map(
        id=MapId(mem[0xD3AB]),
        height=mem[0xD571],
        width=mem[0xD572],
        grass_tile=mem[0xD582],
        water_tile=mem[3, 0x68A5],
        ledge_tiles=ledge_tiles,
        cut_tree_tiles=cut_tree_tiles,
        walkable_tiles=walkable_tiles,
        north_connection=MapId(mem[0xD3BE]) if mem[0xD3BE] != terminator else None,
        south_connection=MapId(mem[0xD3C9]) if mem[0xD3C9] != terminator else None,
        east_connection=MapId(mem[0xD3DF]) if mem[0xD3DF] != terminator else None,
        west_connection=MapId(mem[0xD3D4]) if mem[0xD3D4] != terminator else None,
    )
