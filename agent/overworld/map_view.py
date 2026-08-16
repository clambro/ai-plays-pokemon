"""Derived navigation view of the player's current map region."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from agent.overworld import navigation
from common.enums import AsciiTile
from common.schemas import Coords
from overworld_map.views import get_current_map_tiles

if TYPE_CHECKING:
    from common.enums import FacingDirection
    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap


@dataclass(slots=True, frozen=True, kw_only=True)
class CurrentMapView:
    """Ephemeral agent-facing view of one reachable region of an explored map."""

    overworld_map: OverworldMap
    navigation_tiles: np.ndarray
    reachable_coords: frozenset[Coords]
    visible_coords: frozenset[Coords]
    display_origin: Coords
    display_tiles: np.ndarray
    exploration_candidates: tuple[Coords, ...]
    boundary_tiles: dict[FacingDirection, tuple[Coords, ...]]


def build_current_map_view(
    overworld_map: OverworldMap,
    game_state: GameState,
) -> CurrentMapView:
    """Build the current reachable region using the shared overworld traversal rules."""
    navigation_tiles = get_current_map_tiles(overworld_map, game_state)
    reachable = navigation.get_accessible_coords(
        game_state.player.coords,
        navigation_tiles,
        overworld_map.blockages,
        game_state.get_hm_tiles(),
    )
    reachable_coords = frozenset(reachable)
    visible_coords = _get_visible_coords(reachable_coords, navigation_tiles)
    display_top = min(coords.row for coords in visible_coords)
    display_bottom = max(coords.row for coords in visible_coords)
    display_left = min(coords.col for coords in visible_coords)
    display_right = max(coords.col for coords in visible_coords)
    region_tiles = navigation_tiles[
        display_top : display_bottom + 1,
        display_left : display_right + 1,
    ]
    display_tiles = np.where(
        region_tiles == AsciiTile.WALL,
        region_tiles,
        AsciiTile.OUTSIDE_REGION,
    )
    for coords in visible_coords:
        display_tiles[coords.row - display_top, coords.col - display_left] = navigation_tiles[
            coords.row,
            coords.col,
        ]

    boundary_tiles = {
        direction: tuple(coords)
        for direction, coords in navigation.get_map_boundary_tiles(
            reachable,
            overworld_map,
        ).items()
    }
    return CurrentMapView(
        overworld_map=overworld_map,
        navigation_tiles=navigation_tiles,
        reachable_coords=reachable_coords,
        visible_coords=visible_coords,
        display_origin=Coords(row=display_top, col=display_left),
        display_tiles=display_tiles,
        exploration_candidates=tuple(
            navigation.get_exploration_candidates(reachable, navigation_tiles),
        ),
        boundary_tiles=boundary_tiles,
    )


def _get_visible_coords(
    reachable_coords: frozenset[Coords],
    navigation_tiles: np.ndarray,
) -> frozenset[Coords]:
    """Include the reachable region and the terrain immediately bounding it."""
    visible = set(reachable_coords)
    height, width = navigation_tiles.shape
    walkable_tiles = set(AsciiTile.get_walkable_tiles())
    spinner_tiles = set(AsciiTile.get_spinner_tiles())
    for coords in reachable_coords:
        for row_offset, col_offset in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            neighbor = coords + (row_offset, col_offset)  # noqa: RUF005
            if not (0 <= neighbor.row < height and 0 <= neighbor.col < width):
                continue
            tile = navigation_tiles[neighbor.row, neighbor.col]
            if tile in spinner_tiles:
                spinner_path = navigation.get_spinner_path(neighbor, navigation_tiles)
                if spinner_path is not None:
                    visible.update(spinner_path)
                continue
            if tile == AsciiTile.UNSEEN or tile not in walkable_tiles:
                visible.add(neighbor)
    return frozenset(visible)
