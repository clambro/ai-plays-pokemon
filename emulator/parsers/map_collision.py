"""Read collision tiles from the map currently loaded in emulator memory."""

from typing import TYPE_CHECKING

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


def read_map_collision_tiles(mem: PyBoyMemoryView) -> list[list[int]]:
    """Expand the loaded map's block grid into collision tiles."""
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


def read_map_collision_tile(mem: PyBoyMemoryView, coords: Coords) -> int | None:
    """Read one collision tile, or return ``None`` outside the loaded map."""
    height = mem[0xD571]
    width = mem[0xD572]
    if coords.row < 0 or coords.row >= height or coords.col < 0 or coords.col >= width:
        return None

    block_stride = mem[_MAP_BLOCK_WIDTH_ADDRESS] + _MAP_BORDER_BLOCKS * 2
    block_address = (
        _OVERWORLD_MAP_ADDRESS
        + (coords.row // 2 + _MAP_BORDER_BLOCKS) * block_stride
        + coords.col // 2
        + _MAP_BORDER_BLOCKS
    )
    block_id = mem[block_address]
    tile_row = coords.row % 2 * _MAP_CELL_TILE_WIDTH + _COLLISION_TILE_ROW_OFFSET
    tile_col = coords.col % 2 * _MAP_CELL_TILE_WIDTH
    tile_offset = tile_row * _BLOCK_TILE_WIDTH + tile_col
    tileset_bank = mem[_TILESET_BANK_ADDRESS]
    blocks_pointer = mem[_TILESET_BLOCKS_POINTER_ADDRESS] | (
        mem[_TILESET_BLOCKS_POINTER_ADDRESS + 1] << 8
    )
    return mem[tileset_bank, blocks_pointer + block_id * _BLOCK_TILE_COUNT + tile_offset]
