"""Derived navigation view of the player's current map region."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from agent.overworld import navigation
from common.enums import AsciiTile, FacingDirection
from common.schemas import Coords
from overworld_map.views import get_current_map_tiles

if TYPE_CHECKING:
    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap


@dataclass(slots=True, frozen=True, kw_only=True)
class ObjectInteractionPosition:
    """A reachable position and facing direction for using one object."""

    coords: Coords
    direction: FacingDirection


@dataclass(slots=True, frozen=True, kw_only=True)
class CurrentMapView:
    """Ephemeral agent-facing view of one reachable region of an explored map."""

    overworld_map: OverworldMap
    navigation_tiles: np.ndarray
    reachable_coords: frozenset[Coords]
    visible_coords: frozenset[Coords]
    counter_interactions: dict[int, tuple[Coords, ...]]
    object_interaction_positions: dict[int, tuple[ObjectInteractionPosition, ...]]
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
    hm_tiles = game_state.get_hm_tiles()
    reachable = navigation.get_accessible_coords(
        game_state.player.coords,
        navigation_tiles,
        overworld_map.blockages,
        hm_tiles,
    )
    reachable_coords = frozenset(reachable)
    counter_interactions = _get_counter_interactions(
        reachable_coords,
        navigation_tiles,
        overworld_map,
        game_state,
    )
    object_interaction_positions = _get_object_interaction_positions(
        reachable_coords,
        overworld_map,
        game_state,
    )
    visible_coords = _get_visible_coords(reachable_coords, navigation_tiles) | frozenset(
        game_state.sprites[entity_id].coords for entity_id in counter_interactions
    )
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
            game_state.map,
            can_surf=AsciiTile.WATER in hm_tiles or game_state.player.is_surfing,
        ).items()
    }
    return CurrentMapView(
        overworld_map=overworld_map,
        navigation_tiles=navigation_tiles,
        reachable_coords=reachable_coords,
        visible_coords=visible_coords,
        counter_interactions=counter_interactions,
        object_interaction_positions=object_interaction_positions,
        display_origin=Coords(row=display_top, col=display_left),
        display_tiles=display_tiles,
        exploration_candidates=tuple(
            navigation.get_exploration_candidates(reachable, navigation_tiles),
        ),
        boundary_tiles=boundary_tiles,
    )


def _get_counter_interactions(
    reachable_coords: frozenset[Coords],
    navigation_tiles: np.ndarray,
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
                and navigation_tiles[counter.row, counter.col] == AsciiTile.COUNTER
            ):
                positions.append(standing)
        if positions:
            interactions[entity_id] = tuple(positions)
    return interactions


def _get_object_interaction_positions(
    reachable_coords: frozenset[Coords],
    overworld_map: OverworldMap,
    game_state: GameState,
) -> dict[int, tuple[ObjectInteractionPosition, ...]]:
    """Find reachable adjacent positions from which each known object can be used."""
    interactions = {}
    offsets = (
        ((1, 0), FacingDirection.UP),
        ((-1, 0), FacingDirection.DOWN),
        ((0, -1), FacingDirection.RIGHT),
        ((0, 1), FacingDirection.LEFT),
    )
    for entity_id in sorted(overworld_map.known_object_ids):
        obj = game_state.objects.get(entity_id)
        if obj is None:
            continue
        positions = tuple(
            ObjectInteractionPosition(
                coords=obj.coords + offset,
                direction=direction,
            )
            for offset, direction in offsets
            if obj.coords + offset in reachable_coords
            and (obj.interaction_direction is None or obj.interaction_direction == direction)
        )
        if positions:
            interactions[entity_id] = positions
    return interactions


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
