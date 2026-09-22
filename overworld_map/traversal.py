"""Shared overworld traversal, reachability, and visibility calculations."""

from collections import deque
from typing import TYPE_CHECKING

import numpy as np

from common.enums import BUTTON_OFFSETS, AsciiTile, BlockedDirection, Button, FacingDirection
from common.schemas import Coords
from overworld_map.tiles import get_navigation_tiles

if TYPE_CHECKING:
    from collections.abc import Mapping

    from emulator.game_state import GameState
    from emulator.parsers.map import Map
    from overworld_map.schemas import OverworldMap


def build_routing_data(
    overworld_map: OverworldMap,
    game_state: GameState,
) -> tuple[np.ndarray, list[Coords]]:
    """Build routing tiles and reachable coordinates without modifying remembered terrain.

    Returns:
        Finished routing tiles and reachable coordinates in traversal order.
    """
    persistent_tiles = overworld_map.terrain_ndarray
    routing_tiles = get_navigation_tiles(overworld_map, game_state)
    # Allow departure from the starting warp without hiding transitions beneath Pikachu.
    player_coords = game_state.player.coords
    routing_tiles[player_coords.row, player_coords.col] = AsciiTile.PLAYER
    spinner_types = [*AsciiTile.get_spinner_tiles(), AsciiTile.SPINNER_STOP]
    # Entity overlays must not hide directional or stop tiles from spinner tracing.
    spinner_mask = np.isin(persistent_tiles, spinner_types)
    routing_tiles[spinner_mask] = persistent_tiles[spinner_mask]
    hm_tiles = game_state.get_hm_tiles()
    reachable_list = get_accessible_coords(
        game_state.player.coords,
        routing_tiles,
        overworld_map.blockages,
        hm_tiles,
    )
    return routing_tiles, reachable_list


def get_exploration_candidates(
    accessible_coords: list[Coords],
    tiles: np.ndarray,
) -> list[Coords]:
    """Get reachable exploration frontiers, including unresolved spinner entries.

    Args:
        accessible_coords: Coordinates the player can currently reach.
        tiles: Current navigation tiles containing known and unseen terrain.

    Returns:
        Reachable coordinates from which the player can reveal unseen terrain.
    """
    candidates = []
    height, width = tiles.shape
    spinner_tiles = AsciiTile.get_spinner_tiles()

    for c in accessible_coords:
        if tiles[c.row, c.col] in spinner_tiles and get_spinner_destination(c, tiles) is None:
            candidates.append(c)
            continue
        for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            ny, nx = c.row + dy, c.col + dx
            if 0 <= ny < height and 0 <= nx < width and tiles[ny, nx] == AsciiTile.UNSEEN:
                candidates.append(c)
                break

    return candidates


def get_map_boundary_tiles(
    accessible_coords: list[Coords],
    map_state: Map,
    *,
    can_surf: bool,
) -> dict[FacingDirection, list[Coords]]:
    """Get all accessible coordinates on connected map boundaries.

    Args:
        accessible_coords: Coordinates the player can currently reach.
        map_state: Current map dimensions, connections, and traversal metadata.
        can_surf: Whether the player can traverse water.

    Returns:
        Accessible boundary coordinates grouped by their cardinal direction.
    """
    height = map_state.height
    width = map_state.width
    boundary_tiles = {
        FacingDirection.UP: [],
        FacingDirection.DOWN: [],
        FacingDirection.LEFT: [],
        FacingDirection.RIGHT: [],
    }

    for c in accessible_coords:
        if (
            c.row == 0
            and map_state.north_connection is not None
            and c.col in map_state.north_connection.source_coordinates
            and map_state.is_connection_crossable(
                map_state.north_connection,
                c,
                can_surf=can_surf,
            )
        ):
            boundary_tiles[FacingDirection.UP].append(c)
        elif (
            c.row == height - 1
            and map_state.south_connection is not None
            and c.col in map_state.south_connection.source_coordinates
            and map_state.is_connection_crossable(
                map_state.south_connection,
                c,
                can_surf=can_surf,
            )
        ):
            boundary_tiles[FacingDirection.DOWN].append(c)
        elif (
            c.col == 0
            and map_state.west_connection is not None
            and c.row in map_state.west_connection.source_coordinates
            and map_state.is_connection_crossable(
                map_state.west_connection,
                c,
                can_surf=can_surf,
            )
        ):
            boundary_tiles[FacingDirection.LEFT].append(c)
        elif (
            c.col == width - 1
            and map_state.east_connection is not None
            and c.row in map_state.east_connection.source_coordinates
            and map_state.is_connection_crossable(
                map_state.east_connection,
                c,
                can_surf=can_surf,
            )
        ):
            boundary_tiles[FacingDirection.RIGHT].append(c)

    return boundary_tiles


def get_accessible_coords(
    start_pos: Coords,
    tiles: np.ndarray,
    blockages: Mapping[Coords, BlockedDirection],
    hm_tiles: list[AsciiTile],
) -> list[Coords]:
    """Find every coordinate reachable from the player's position.

    Args:
        start_pos: Coordinate at which to begin the search.
        tiles: Current navigation tiles.
        blockages: Known paired-tile movement blockages.
        hm_tiles: Additional tile types traversable with the player's current HMs.

    Returns:
        Reachable coordinates, including ``start_pos`` so a boundary beneath the player is found.
    """
    visited = {start_pos}
    queue = deque([start_pos])
    accessible = [start_pos]
    while queue:
        current = queue.popleft()
        for neighbor, _ in get_neighbors(current, tiles, blockages, hm_tiles):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                accessible.append(neighbor)

    return accessible


def get_neighbors(
    pos: Coords,
    tiles: np.ndarray,
    blockages: Mapping[Coords, BlockedDirection],
    hm_tiles: list[AsciiTile],
) -> list[tuple[Coords, Button]]:
    """Get valid neighboring coordinates from a position.

    Args:
        pos: Coordinate whose neighbors should be evaluated.
        tiles: Current navigation tiles.
        blockages: Known paired-tile movement blockages.
        hm_tiles: Additional tile types traversable with the player's current HMs.

    Returns:
        Reachable neighboring coordinates paired with the button that enters each one.
    """
    neighbors: list[tuple[Coords, Button]] = []
    walkable_tiles = AsciiTile.get_walkable_tiles()
    spinner_tiles = AsciiTile.get_spinner_tiles()

    current_tile = tiles[pos.row, pos.col]
    if current_tile in AsciiTile.get_step_on_transition_tiles() or current_tile in spinner_tiles:
        return []  # These transition tiles cannot be used as stable intermediate positions.

    for button in (Button.RIGHT, Button.DOWN, Button.LEFT, Button.UP):
        dy, dx = BUTTON_OFFSETS[button]
        new_pos = pos + (dy, dx)  # noqa: RUF005

        if (
            new_pos.row < 0
            or new_pos.row >= tiles.shape[0]
            or new_pos.col < 0
            or new_pos.col >= tiles.shape[1]
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
            if not (0 <= ledge_pos.row < tiles.shape[0] and 0 <= ledge_pos.col < tiles.shape[1]):
                ledge_pos = new_pos
            neighbors.append((ledge_pos, button))
        elif target_tile in spinner_tiles:
            destination = get_spinner_destination(new_pos, tiles)
            # An unresolved spinner is still reachable as an exploration action, but it is
            # terminal until traversing it reveals where it leads.
            neighbors.append((destination if destination is not None else new_pos, button))
        elif not is_blocked(pos, dy, dx, blockages) and (
            target_tile in walkable_tiles
            or (target_tile == AsciiTile.CUT_TREE and AsciiTile.CUT_TREE in hm_tiles)
            or (target_tile == AsciiTile.WATER and AsciiTile.WATER in hm_tiles)
        ):
            neighbors.append((new_pos, button))

    return neighbors


def is_blocked(
    current: Coords,
    dy: int,
    dx: int,
    blockages: Mapping[Coords, BlockedDirection],
) -> bool:
    """Check if the movement is blocked by a paired tile collision."""
    blocked_directions = blockages.get(current)
    if not blocked_directions:
        return False
    if dy == 1:
        return bool(blocked_directions & BlockedDirection.DOWN)
    if dy == -1:
        return bool(blocked_directions & BlockedDirection.UP)
    if dx == 1:
        return bool(blocked_directions & BlockedDirection.RIGHT)
    if dx == -1:
        return bool(blocked_directions & BlockedDirection.LEFT)
    return False


def get_spinner_destination(pos: Coords, tiles: np.ndarray) -> Coords | None:
    """Get a spinner's known destination, if its full path has been revealed."""
    path = get_spinner_path(pos, tiles)
    if path is None:
        return None
    destination = path[-1]
    return (
        destination if tiles[destination.row, destination.col] == AsciiTile.SPINNER_STOP else None
    )


def get_spinner_path(pos: Coords, tiles: np.ndarray) -> tuple[Coords, ...] | None:
    """Trace a spinner to its stop or the first unseen tile, inclusive.

    Return ``None`` for a non-spinner start or a path that leaves the map.
    """
    height, width = tiles.shape
    if not (0 <= pos.row < height and 0 <= pos.col < width):
        return None

    path = [pos]
    tile = tiles[pos.row, pos.col]
    if tile not in _SPINNER_DIRECTION_MAP:
        return None
    direction = _SPINNER_DIRECTION_MAP[tile]

    while True:
        new_pos = pos + direction
        if not (0 <= new_pos.row < height and 0 <= new_pos.col < width):
            return None
        new_tile = tiles[new_pos.row, new_pos.col]
        path.append(new_pos)
        if new_tile in (AsciiTile.SPINNER_STOP, AsciiTile.UNSEEN):
            return tuple(path)
        if new_tile in AsciiTile.get_spinner_tiles():
            direction = _SPINNER_DIRECTION_MAP[new_tile]
        pos = new_pos


_SPINNER_DIRECTION_MAP = {
    AsciiTile.SPINNER_UP: Coords(row=-1, col=0),
    AsciiTile.SPINNER_DOWN: Coords(row=1, col=0),
    AsciiTile.SPINNER_LEFT: Coords(row=0, col=-1),
    AsciiTile.SPINNER_RIGHT: Coords(row=0, col=1),
}


def get_counter_interactions(
    reachable_coords: frozenset[Coords],
    routing_tiles: np.ndarray,
    overworld_map: OverworldMap,
    game_state: GameState,
) -> dict[int, tuple[Coords, ...]]:
    """Find reachable positions from which the ROM permits talking across a counter."""
    interactions = {}
    for entity_id in sorted(overworld_map.known_sprite_ids):
        sprite = game_state.sprites.get(entity_id)
        if sprite is None:
            continue
        positions = []
        for row_offset, col_offset in ((-1, 0), (0, -1), (0, 1), (1, 0)):
            counter = Coords(
                row=sprite.coords.row + row_offset,
                col=sprite.coords.col + col_offset,
            )
            standing = Coords(
                row=sprite.coords.row + row_offset * 2,
                col=sprite.coords.col + col_offset * 2,
            )
            if (
                standing in reachable_coords
                and routing_tiles[counter.row, counter.col] == AsciiTile.COUNTER
            ):
                positions.append(standing)
        if positions:
            interactions[entity_id] = tuple(positions)
    return interactions


def get_visible_coords(
    reachable_coords: frozenset[Coords],
    routing_tiles: np.ndarray,
) -> frozenset[Coords]:
    """Include the reachable region and the terrain immediately bounding it."""
    visible = set(reachable_coords)
    height, width = routing_tiles.shape
    walkable_tiles = set(AsciiTile.get_walkable_tiles())
    spinner_tiles = set(AsciiTile.get_spinner_tiles())
    for coords in reachable_coords:
        for row_offset, col_offset in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            neighbor = coords + (row_offset, col_offset)  # noqa: RUF005
            if not (0 <= neighbor.row < height and 0 <= neighbor.col < width):
                continue
            tile = routing_tiles[neighbor.row, neighbor.col]
            if tile in spinner_tiles:
                spinner_path = get_spinner_path(neighbor, routing_tiles)
                if spinner_path is not None:
                    visible.update(spinner_path)
                continue
            if tile == AsciiTile.UNSEEN or tile not in walkable_tiles:
                visible.add(neighbor)
    return frozenset(visible)
