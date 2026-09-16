"""Derived navigation view of the player's current map region."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from common.enums import AsciiTile, FacingDirection
from common.schemas import Coords
from overworld_map.tiles import get_composed_map_tiles
from overworld_map.traversal import (
    build_routing_data,
    get_counter_interactions,
    get_exploration_candidates,
    get_map_boundary_tiles,
    get_visible_coords,
)

if TYPE_CHECKING:
    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap


@dataclass(slots=True, frozen=True, kw_only=True)
class InteractionPosition:
    """A reachable position and facing direction for using a map interaction."""

    coords: Coords
    direction: FacingDirection


@dataclass(slots=True, frozen=True, kw_only=True)
class LockedDoor:
    """One reachable locked door represented by its ROM map block."""

    block_coords: Coords
    tile_coords: tuple[Coords, ...]
    interaction_positions: tuple[InteractionPosition, ...]


@dataclass(slots=True, frozen=True, kw_only=True)
class CurrentMapView:
    """Ephemeral agent-facing view of one reachable region of an explored map."""

    overworld_map: OverworldMap
    routing_tiles: np.ndarray
    reachable_coords: frozenset[Coords]
    visible_coords: frozenset[Coords]
    counter_interactions: dict[int, tuple[Coords, ...]]
    object_interaction_positions: dict[int, tuple[InteractionPosition, ...]]
    locked_doors: tuple[LockedDoor, ...]
    display_origin: Coords
    display_tiles: np.ndarray
    exploration_candidates: tuple[Coords, ...]
    boundary_tiles: dict[FacingDirection, tuple[Coords, ...]]


def build_current_map_view(
    overworld_map: OverworldMap,
    game_state: GameState,
) -> CurrentMapView:
    """Build the current reachable region using the shared overworld traversal rules."""
    composed_tiles = get_composed_map_tiles(overworld_map, game_state)
    routing_tiles, reachable_list = build_routing_data(overworld_map, game_state)
    hm_tiles = game_state.get_hm_tiles()
    reachable_coords = frozenset(reachable_list)
    counter_interactions = get_counter_interactions(
        reachable_coords,
        routing_tiles,
        overworld_map,
        game_state,
    )
    object_interaction_positions = _get_object_interaction_positions(
        reachable_coords,
        overworld_map,
        game_state,
    )
    locked_doors = _get_locked_doors(reachable_coords, overworld_map)
    visible_coords = get_visible_coords(reachable_coords, routing_tiles) | frozenset(
        game_state.sprites[entity_id].coords for entity_id in counter_interactions
    )
    display_top = min(coords.row for coords in visible_coords)
    display_bottom = max(coords.row for coords in visible_coords)
    display_left = min(coords.col for coords in visible_coords)
    display_right = max(coords.col for coords in visible_coords)
    display_crop = composed_tiles[
        display_top : display_bottom + 1,
        display_left : display_right + 1,
    ]
    display_tiles = np.where(
        np.isin(display_crop, (AsciiTile.WALL, AsciiTile.LOCKED_DOOR)),
        display_crop,
        AsciiTile.OUTSIDE_REGION,
    )
    for coords in visible_coords:
        display_tiles[coords.row - display_top, coords.col - display_left] = composed_tiles[
            coords.row,
            coords.col,
        ]

    boundary_tiles = {
        direction: tuple(coords)
        for direction, coords in get_map_boundary_tiles(
            reachable_list,
            game_state.map,
            can_surf=AsciiTile.WATER in hm_tiles or game_state.player.is_surfing,
        ).items()
    }
    return CurrentMapView(
        overworld_map=overworld_map,
        routing_tiles=routing_tiles,
        reachable_coords=reachable_coords,
        visible_coords=visible_coords,
        counter_interactions=counter_interactions,
        object_interaction_positions=object_interaction_positions,
        locked_doors=locked_doors,
        display_origin=Coords(row=display_top, col=display_left),
        display_tiles=display_tiles,
        exploration_candidates=tuple(
            get_exploration_candidates(reachable_list, routing_tiles),
        ),
        boundary_tiles=boundary_tiles,
    )


def _get_object_interaction_positions(
    reachable_coords: frozenset[Coords],
    overworld_map: OverworldMap,
    game_state: GameState,
) -> dict[int, tuple[InteractionPosition, ...]]:
    """Find reachable adjacent positions from which each known object can be used."""
    interactions = {}
    for entity_id in sorted(overworld_map.known_object_ids):
        obj = game_state.objects.get(entity_id)
        if obj is None:
            continue
        positions = _get_adjacent_interaction_positions(
            obj.coords,
            reachable_coords,
            obj.interaction_direction,
        )
        if positions:
            interactions[entity_id] = positions
    return interactions


def _get_locked_doors(
    reachable_coords: frozenset[Coords],
    overworld_map: OverworldMap,
) -> tuple[LockedDoor, ...]:
    """Find reachable locked doors, identified by their ROM map block."""
    door_coords_by_block: dict[Coords, list[Coords]] = {}
    for row, col in np.argwhere(overworld_map.terrain_ndarray == AsciiTile.LOCKED_DOOR):
        coords = Coords(row=int(row), col=int(col))
        block_coords = Coords(row=coords.row // 2, col=coords.col // 2)
        door_coords_by_block.setdefault(block_coords, []).append(coords)

    doors = []
    for block_coords, door_coords in sorted(
        door_coords_by_block.items(),
        key=lambda item: (item[0].row, item[0].col),
    ):
        interaction_positions = tuple(
            dict.fromkeys(
                position
                for coords in door_coords
                for position in _get_adjacent_interaction_positions(
                    coords,
                    reachable_coords,
                    None,
                )
            )
        )
        if interaction_positions:
            doors.append(
                LockedDoor(
                    block_coords=block_coords,
                    tile_coords=tuple(door_coords),
                    interaction_positions=interaction_positions,
                )
            )
    return tuple(doors)


def _get_adjacent_interaction_positions(
    target: Coords,
    reachable_coords: frozenset[Coords],
    required_direction: FacingDirection | None,
) -> tuple[InteractionPosition, ...]:
    """Find reachable positions from which one target can be used."""
    offsets = (
        ((1, 0), FacingDirection.UP),
        ((-1, 0), FacingDirection.DOWN),
        ((0, -1), FacingDirection.RIGHT),
        ((0, 1), FacingDirection.LEFT),
    )
    return tuple(
        InteractionPosition(
            coords=target + offset,
            direction=direction,
        )
        for offset, direction in offsets
        if target + offset in reachable_coords
        and (required_direction is None or required_direction == direction)
    )
