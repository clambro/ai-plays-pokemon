"""Pure algorithmic logic for navigation operations.

This module contains the core algorithmic functions for navigation, separate from any formatting
concerns to make them easier to test.
"""

from typing import TYPE_CHECKING

from common.enums import AsciiTile, BlockedDirection, Button, FacingDirection
from common.schemas import Coords

if TYPE_CHECKING:
    import numpy as np

    from overworld_map.schemas import OverworldMap


def get_exploration_candidates(
    accessible_coords: list[Coords],
    map_data: OverworldMap,
) -> list[Coords]:
    """Get all accessible coordinates adjacent to an unseen tile.

    Args:
        accessible_coords: Coordinates the player can currently reach.
        map_data: Explored map containing known and unseen tiles.

    Returns:
        Reachable coordinates from which the player can reveal unseen terrain.
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
    """Get all accessible coordinates on connected map boundaries.

    Args:
        accessible_coords: Coordinates the player can currently reach.
        map_data: Explored map and its cardinal connections.

    Returns:
        Accessible boundary coordinates grouped by their cardinal direction.
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
        if (
            c.row == 0
            and map_data.north_connection is not None
            and c.col in map_data.north_connection.source_coordinates
        ):
            boundary_tiles[FacingDirection.UP].append(c)
        elif (
            c.row == height - 1
            and map_data.south_connection is not None
            and c.col in map_data.south_connection.source_coordinates
        ):
            boundary_tiles[FacingDirection.DOWN].append(c)
        elif (
            c.col == 0
            and map_data.west_connection is not None
            and c.row in map_data.west_connection.source_coordinates
        ):
            boundary_tiles[FacingDirection.LEFT].append(c)
        elif (
            c.col == width - 1
            and map_data.east_connection is not None
            and c.row in map_data.east_connection.source_coordinates
        ):
            boundary_tiles[FacingDirection.RIGHT].append(c)

    return boundary_tiles


def get_accessible_coords(
    start_pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[Coords]:
    """Find every coordinate reachable from the player's position.

    Args:
        start_pos: Coordinate at which to begin the search.
        map_data: Explored map containing tiles and paired-tile blockages.
        hm_tiles: Additional tile types traversable with the player's current HMs.

    Returns:
        Reachable coordinates, including ``start_pos`` so a boundary beneath the player is found.
    """
    visited = {start_pos}
    queue = [start_pos]
    accessible = [start_pos]
    while queue:
        current = queue.pop(0)
        for neighbor, _ in _get_neighbors(current, map_data, hm_tiles):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                accessible.append(neighbor)

    return accessible


def calculate_path_to_target(
    start_pos: Coords,
    target_pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[Button] | None:
    """Calculate an A* path to the target as a sequence of button presses.

    Args:
        start_pos: Coordinate at which to begin the path.
        target_pos: Coordinate the path should reach.
        map_data: Explored map containing tiles and paired-tile blockages.
        hm_tiles: Additional tile types traversable with the player's current HMs.

    Returns:
        Button presses reaching the target, or ``None`` when no path exists.
    """
    open_set = {start_pos}
    came_from: dict[Coords, tuple[Coords, Button]] = {}
    g_score = {start_pos: 0}
    f_score = {start_pos: (start_pos - target_pos).length}
    tile_arr = map_data.ascii_tiles_ndarray
    expensive_tiles = [
        AsciiTile.GRASS,
        AsciiTile.CUT_TREE,
        AsciiTile.WATER,
        *AsciiTile.get_spinner_tiles(),
    ]

    while open_set:
        current = min(open_set, key=lambda pos: f_score.get(pos, float("inf")))

        if current == target_pos:
            # Reconstruct path and convert to button presses
            path = []
            while current in came_from:
                prev, button = came_from[current]
                path.append(button)
                current = prev

            return list(reversed(path))  # Reverse to get start->target order

        open_set.remove(current)

        for neighbor, button in _get_neighbors(current, map_data, hm_tiles):
            # Bias movement away from tiles that take more time to traverse.
            increment = 5 if tile_arr[neighbor.row, neighbor.col] in expensive_tiles else 1
            tentative_g_score = g_score[current] + increment

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = (current, button)
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + (neighbor - target_pos).length
                open_set.add(neighbor)

    # If we get here, no path was found
    return None


def _get_neighbors(
    pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[tuple[Coords, Button]]:
    """Get valid neighboring coordinates from a position.

    Args:
        pos: Coordinate whose neighbors should be evaluated.
        map_data: Explored map containing tiles and paired-tile blockages.
        hm_tiles: Additional tile types traversable with the player's current HMs.

    Returns:
        Reachable neighboring coordinates paired with the button that enters each one.
    """
    neighbors: list[tuple[Coords, Button]] = []
    walkable_tiles = AsciiTile.get_walkable_tiles()
    spinner_tiles = AsciiTile.get_spinner_tiles()

    tiles = map_data.ascii_tiles_ndarray
    current_tile = tiles[pos.row, pos.col]
    if current_tile in [AsciiTile.WARP, AsciiTile.BOULDER_HOLE] or current_tile in spinner_tiles:
        return []  # These transition tiles cannot be used as stable intermediate positions.

    for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
        new_pos = pos + (dy, dx)  # noqa: RUF005
        button = _DIRECTION_BUTTON_MAP[(dy, dx)]

        if (
            new_pos.row < 0
            or new_pos.row >= map_data.height
            or new_pos.col < 0
            or new_pos.col >= map_data.width
        ):
            continue

        target_tile = tiles[new_pos.row, new_pos.col]

        if (
            (target_tile == AsciiTile.LEDGE_DOWN and dy == 1)
            or (target_tile == AsciiTile.LEDGE_LEFT and dx == -1)
            or (target_tile == AsciiTile.LEDGE_RIGHT and dx == 1)
        ):
            # Jumping over a ledge skips a tile.
            ledge_pos = new_pos + (dy, dx)  # noqa: RUF005
            neighbors.append((ledge_pos, button))
        elif target_tile in spinner_tiles:
            destination = get_spinner_destination(new_pos, tiles)
            # An unresolved spinner is still reachable as an exploration action, but it is
            # terminal until traversing it reveals where it leads.
            neighbors.append((destination if destination is not None else new_pos, button))
        elif not _is_blocked(pos, dy, dx, map_data) and (
            target_tile in walkable_tiles
            or (target_tile == AsciiTile.CUT_TREE and AsciiTile.CUT_TREE in hm_tiles)
            or (target_tile == AsciiTile.WATER and AsciiTile.WATER in hm_tiles)
        ):
            neighbors.append((new_pos, button))

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


def get_spinner_destination(pos: Coords, tiles: np.ndarray) -> Coords | None:
    """Get a spinner's known destination, if its full path has been revealed."""
    tile = tiles[pos.row, pos.col]
    direction = _SPINNER_DIRECTION_MAP[tile]

    while True:
        new_pos = pos + direction
        new_tile = tiles[new_pos.row, new_pos.col]
        if new_tile == AsciiTile.UNSEEN:
            return None
        if new_tile == AsciiTile.SPINNER_STOP:
            return new_pos
        if new_tile in AsciiTile.get_spinner_tiles():
            direction = _SPINNER_DIRECTION_MAP[new_tile]
        pos = new_pos


_DIRECTION_BUTTON_MAP = {
    (0, 1): Button.RIGHT,
    (1, 0): Button.DOWN,
    (0, -1): Button.LEFT,
    (-1, 0): Button.UP,
}

_SPINNER_DIRECTION_MAP = {
    AsciiTile.SPINNER_UP: Coords(row=-1, col=0),
    AsciiTile.SPINNER_DOWN: Coords(row=1, col=0),
    AsciiTile.SPINNER_LEFT: Coords(row=0, col=-1),
    AsciiTile.SPINNER_RIGHT: Coords(row=0, col=1),
}
