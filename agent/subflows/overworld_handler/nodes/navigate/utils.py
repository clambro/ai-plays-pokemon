"""
Pure algorithmic logic for navigation operations.

This module contains the core algorithmic functions for navigation, separate from any formatting
concerns to make them easier to test.
"""

import asyncio

import numpy as np

from common.enums import AsciiTile, BlockedDirection, Button, FacingDirection
from common.schemas import Coords
from overworld_map.schemas import OverworldMap


async def get_accessible_coords(
    start_pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[Coords]:
    """
    Recursively search outward from the player's position to find all accessible coords. Do this
    on a thread because it's pretty slow.

    :param start_pos: Starting position to search from
    :param map_data: Map data containing tiles and blockages
    :param walkable_tiles: List of tiles that are accessible using the player's current HMs.
    :return: List of accessible coordinates, including start_pos (required for finding map
        boundaries if you're standing on a boundary tile)
    """
    return await asyncio.to_thread(_get_accessible_coords, start_pos, map_data, hm_tiles)


async def calculate_path_to_target(
    start_pos: Coords,
    target_pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[Button] | None:
    """
    Calculate the path to the target coordinates as a list of button presses using the A* search
    algorithm. Do this on a thread because it's pretty slow.

    :param start_pos: Starting position
    :param target_pos: Target position
    :param map_data: Map data containing tiles and blockages
    :param hm_tiles: List of tiles that are accessible using the player's current HMs.
    :return: List of button presses to reach target, or None if no path found
    """
    return await asyncio.to_thread(
        _calculate_path_to_target,
        start_pos,
        target_pos,
        map_data,
        hm_tiles,
    )


def get_exploration_candidates(
    accessible_coords: list[Coords],
    map_data: OverworldMap,
) -> list[Coords]:
    """
    Get all accessible coords that are adjacent to an unseen tile.

    :param accessible_coords: List of accessible coordinates
    :param map_data: Map data containing tiles
    :return: List of coordinates that are adjacent to unseen tiles
    """
    candidates = []
    tiles = map_data.ascii_tiles_ndarray
    height, width = tiles.shape

    for c in accessible_coords:
        for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            ny, nx = c.row + dy, c.col + dx
            if 0 <= ny < height and 0 <= nx < width and tiles[ny, nx] == AsciiTile.UNSEEN:
                candidates.append(c)
                break

    return candidates


def get_map_boundary_tiles(
    accessible_coords: list[Coords],
    map_data: OverworldMap,
) -> dict[FacingDirection, list[Coords]]:
    """
    Get all accessible coords that are on the map boundary.

    :param accessible_coords: List of accessible coordinates
    :param map_data: Map data containing tiles
    :return: Dictionary mapping directions to lists of boundary coordinates
    """
    tiles = map_data.ascii_tiles_ndarray
    height, width = tiles.shape
    boundary_tiles = {
        FacingDirection.UP: [],
        FacingDirection.DOWN: [],
        FacingDirection.LEFT: [],
        FacingDirection.RIGHT: [],
    }

    for c in accessible_coords:
        if c.row == 0 and map_data.north_connection is not None:
            boundary_tiles[FacingDirection.UP].append(c)
        elif c.row == height - 1 and map_data.south_connection is not None:
            boundary_tiles[FacingDirection.DOWN].append(c)
        elif c.col == 0 and map_data.west_connection is not None:
            boundary_tiles[FacingDirection.LEFT].append(c)
        elif c.col == width - 1 and map_data.east_connection is not None:
            boundary_tiles[FacingDirection.RIGHT].append(c)

    return boundary_tiles


def _get_accessible_coords(
    start_pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[Coords]:
    """Recursively search outward from the player's position to find all accessible coords."""
    visited = {start_pos}
    queue = [start_pos]
    accessible = [start_pos]
    while queue:
        current = queue.pop(0)
        for neighbor in _get_neighbors(current, map_data, hm_tiles):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                accessible.append(neighbor)

    return accessible


def _calculate_path_to_target(
    start_pos: Coords,
    target_pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[Button] | None:
    """
    Calculate the path to the target coordinates as a list of button presses using the A* search
    algorithm.

    :param start_pos: Starting position
    :param target_pos: Target position
    :param map_data: Map data containing tiles and blockages
    :param hm_tiles: List of tiles that are accessible using the player's current HMs.
    :return: List of button presses to reach target, or None if no path found
    """
    open_set = {start_pos}
    came_from: dict[Coords, Coords] = {}
    g_score = {start_pos: 0}
    f_score = {start_pos: (start_pos - target_pos).length}
    tile_arr = map_data.ascii_tiles_ndarray

    while open_set:
        current = min(open_set, key=lambda pos: f_score.get(pos, float("inf")))

        if current == target_pos:
            # Reconstruct path and convert to button presses
            path = []
            while current in came_from:
                prev = came_from[current]
                delta = current - prev

                if delta.row > 0:
                    path.append(Button.DOWN)
                elif delta.row < 0:
                    path.append(Button.UP)
                elif delta.col > 0:
                    path.append(Button.RIGHT)
                elif delta.col < 0:
                    path.append(Button.LEFT)

                current = prev

            return list(reversed(path))  # Reverse to get start->target order

        open_set.remove(current)

        for neighbor in _get_neighbors(current, map_data, hm_tiles):
            # Bias movement away from grass tiles.
            increment = 5 if tile_arr[neighbor.row, neighbor.col] == AsciiTile.GRASS else 1
            tentative_g_score = g_score[current] + increment

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + (neighbor - target_pos).length
                open_set.add(neighbor)

    # If we get here, no path was found
    return None


def _get_neighbors(
    pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[Coords]:
    """
    Get all valid neighboring coordinates from a given position.

    :param pos: The position to get neighbors for
    :param map_data: Map data containing tiles and blockages
    :param hm_tiles: List of tiles that are accessible using the player's current HMs.
    :return: List of valid neighboring coordinates
    """
    neighbors = []
    walkable_tiles = AsciiTile.get_walkable_tiles()
    spinner_tiles = AsciiTile.get_spinner_tiles()

    for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
        new_pos = pos + (dy, dx)  # noqa: RUF005

        if (
            new_pos.row < 0
            or new_pos.row >= map_data.height
            or new_pos.col < 0
            or new_pos.col >= map_data.width
        ):
            continue

        tiles = map_data.ascii_tiles_ndarray
        target_tile = tiles[new_pos.row, new_pos.col]

        if not _is_blocked(pos, dy, dx, map_data) and (
            target_tile in walkable_tiles
            or (target_tile == AsciiTile.CUT_TREE and AsciiTile.CUT_TREE in hm_tiles)
        ):
            neighbors.append(new_pos)
        # Jumping over a ledge skips a tile
        elif target_tile == AsciiTile.LEDGE_DOWN and dy == 1:
            ledge_pos = new_pos + (1, 0)  # noqa: RUF005
            neighbors.append(ledge_pos)
        elif target_tile == AsciiTile.LEDGE_LEFT and dx == -1:
            ledge_pos = new_pos + (0, -1)  # noqa: RUF005
            neighbors.append(ledge_pos)
        elif target_tile == AsciiTile.LEDGE_RIGHT and dx == 1:
            ledge_pos = new_pos + (0, 1)  # noqa: RUF005
            neighbors.append(ledge_pos)
        elif target_tile in spinner_tiles:
            destination = _get_spinner_destination(new_pos, tiles)
            neighbors.append(destination)

    return neighbors


def _is_blocked(current: Coords, dy: int, dx: int, map_data: OverworldMap) -> bool:
    """Check if the movement is blocked by a paired tile collision."""
    blockages = map_data.blockages.get(current)
    if not blockages:
        return False
    if dy == 1:
        return bool(blockages & BlockedDirection.DOWN)
    if dy == -1:
        return bool(blockages & BlockedDirection.UP)
    if dx == 1:
        return bool(blockages & BlockedDirection.RIGHT)
    if dx == -1:
        return bool(blockages & BlockedDirection.LEFT)
    return False


def _get_spinner_destination(pos: Coords, tiles: np.ndarray) -> Coords:
    """Get the destination of a spinner tile."""
    tile = tiles[pos.row, pos.col]
    direction = _SPINNER_DIRECTION_MAP[tile]

    while True:
        new_pos = pos + direction
        new_tile = tiles[new_pos.row, new_pos.col]
        # Unseen is an edge case. We don't know where it goes, but we can't follow it any further.
        # Assume we stop just before it. This breaks navigation, but there's nothing we can do
        # until the tile is revealed on the next Agent iteration.
        if new_tile == AsciiTile.UNSEEN:
            return pos
        if new_tile == AsciiTile.SPINNER_STOP:
            return new_pos
        if new_tile in AsciiTile.get_spinner_tiles():
            direction = _SPINNER_DIRECTION_MAP[new_tile]
        pos = new_pos


_SPINNER_DIRECTION_MAP = {
    AsciiTile.SPINNER_UP: Coords(row=-1, col=0),
    AsciiTile.SPINNER_DOWN: Coords(row=1, col=0),
    AsciiTile.SPINNER_LEFT: Coords(row=0, col=-1),
    AsciiTile.SPINNER_RIGHT: Coords(row=0, col=1),
}
