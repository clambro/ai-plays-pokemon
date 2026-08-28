"""Persistence and updates for the explored overworld map."""

from typing import TYPE_CHECKING

from loguru import logger

from common.enums import AsciiTile, Button, FacingDirection, MapEntityType, MapId
from common.schemas import Coords
from database.map_boundary_memory.repository import get_map_boundary_memories_for_map
from database.map_boundary_memory.repository import (
    remember_map_boundaries as persist_map_boundaries,
)
from database.map_boundary_memory.schemas import MapBoundaryMemoryCreateUpdate
from database.map_entity_memory.repository import (
    apply_map_entity_changes,
    get_map_entity_memories_for_map,
    update_map_entity_interactions,
)
from database.map_entity_memory.schemas import (
    MapEntityMemoryCreate,
    MapEntityMemoryDelete,
    MapEntityMemoryInteractionUpdate,
)
from database.map_memory.repository import (
    create_map_memory,
    get_map_memory,
    get_visited_maps,
    update_map_terrain,
)
from database.map_memory.schemas import MapMemoryCreateUpdate
from database.warp_memory.repository import (
    get_warp_memories_for_map,
    remember_warps,
)
from database.warp_memory.repository import record_warp_usage as persist_warp_usage
from database.warp_memory.schemas import WarpMemoryCreateUpdate
from emulator.control_events import ControlBoundary
from overworld_map.schemas import MapEntityInteractionMemory, OverworldMap

if TYPE_CHECKING:
    from emulator.control_events import ControlResult
    from emulator.game_state import GameState
    from emulator.parsers.warp import Warp
    from emulator.schemas import AsciiScreenWithEntities
    from emulator.text_events import CompletedMapEntityInteraction


async def get_overworld_map(iteration: int, game_state: GameState) -> OverworldMap:
    """Load the explored map for a game-state snapshot.

    Existing terrain and discovered entity identities are loaded from the database. An unseen
    map is initialized and persisted before being returned.

    Args:
        iteration: Current agent iteration used when creating new map memory.
        game_state: Current parsed game state and map metadata.

    Returns:
        The explored map populated with remembered entity identities and current map connections.
    """
    map_memory = await get_map_memory(game_state.map.id)
    if map_memory is None:
        return await _create_overworld_map_from_game_state(iteration, game_state)

    map_entity_memories = await get_map_entity_memories_for_map(map_memory.map_id)
    warp_memories = await get_warp_memories_for_map(map_memory.map_id)
    map_boundaries = await get_map_boundary_memories_for_map(map_memory.map_id)

    known_map_ids = frozenset(await get_visited_maps())

    return OverworldMap(
        id=map_memory.map_id,
        terrain=[list(row) for row in map_memory.terrain.split("\n")],
        blockages=map_memory.blockages,
        known_sprite_ids={
            memory.entity_id
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.SPRITE
        },
        sprite_interactions={
            memory.entity_id: MapEntityInteractionMemory(
                text=memory.last_interaction,
                iteration=memory.last_interaction_iteration,
            )
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.SPRITE
            and memory.last_interaction is not None
            and memory.last_interaction_iteration is not None
        },
        known_warp_ids={memory.warp_id for memory in warp_memories},
        warp_usage_iterations={
            memory.warp_id: memory.last_used_iteration
            for memory in warp_memories
            if memory.last_used_iteration is not None
        },
        known_map_boundaries=tuple(map_boundaries),
        known_sign_ids={
            memory.entity_id
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.SIGN
        },
        sign_interactions={
            memory.entity_id: MapEntityInteractionMemory(
                text=memory.last_interaction,
                iteration=memory.last_interaction_iteration,
            )
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.SIGN
            and memory.last_interaction is not None
            and memory.last_interaction_iteration is not None
        },
        known_object_ids={
            memory.entity_id
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.OBJECT
        },
        object_interactions={
            memory.entity_id: MapEntityInteractionMemory(
                text=memory.last_interaction,
                iteration=memory.last_interaction_iteration,
            )
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.OBJECT
            and memory.last_interaction is not None
            and memory.last_interaction_iteration is not None
        },
        known_map_ids=known_map_ids,
        north_connection=game_state.map.north_connection,
        south_connection=game_state.map.south_connection,
        east_connection=game_state.map.east_connection,
        west_connection=game_state.map.west_connection,
    )


async def prepare_overworld_map(
    iteration: int,
    game_state: GameState,
) -> OverworldMap:
    """Load the explored map and apply the current visible observation.

    Args:
        iteration: Current agent iteration used to timestamp persistence updates.
        game_state: Current parsed game state and visible screen.

    Returns:
        The prepared explored map for the agent.
    """
    overworld_map = await get_overworld_map(iteration, game_state)
    await update_overworld_map(iteration, game_state, overworld_map)
    return overworld_map


async def update_overworld_map(
    iteration: int,
    game_state: GameState,
    overworld_map: OverworldMap,
) -> None:
    """Update explored-map memory from the current visible screen.

    Terrain and entities are persisted only when no text obscures the screen and the supplied map
    matches the current game state.

    Args:
        iteration: Current agent iteration used to timestamp persistence updates.
        game_state: Current parsed game state and visible screen.
        overworld_map: Explored map expected to match ``game_state``.
    """
    if not game_state.is_text_on_screen() and overworld_map.id == game_state.map.id:
        ascii_screen = game_state.get_ascii_screen()
        await _add_remove_map_entities(game_state, overworld_map, ascii_screen)
        await remember_warps(
            [_create_warp_memory(overworld_map.id, warp) for warp in ascii_screen.warps]
        )
        overworld_map.known_warp_ids.update(warp.index for warp in ascii_screen.warps)
        await _update_overworld_map_terrain(iteration, game_state, overworld_map)


async def _add_remove_map_entities(
    game_state: GameState,
    overworld_map: OverworldMap,
    ascii_screen: AsciiScreenWithEntities,
) -> None:
    """Add or remove entities from the overworld map depending on the current screen."""
    if overworld_map.id != game_state.map.id:
        raise ValueError("Overworld map does not match current game state.")

    new_sprite_ids = {
        sprite.index
        for sprite in ascii_screen.sprites
        if sprite.is_rendered and sprite.index not in overworld_map.known_sprite_ids
    }
    new_sign_ids = {
        sign.index for sign in ascii_screen.signs if sign.index not in overworld_map.known_sign_ids
    }
    new_object_ids = {
        obj.index for obj in ascii_screen.objects if obj.index not in overworld_map.known_object_ids
    }
    removed_sprite_ids = {
        entity_id
        for entity_id in overworld_map.known_sprite_ids
        if (sprite := game_state.sprites.get(entity_id)) is not None
        if game_state.screen.to_screen_coords(sprite.coords) is not None and not sprite.is_rendered
    }

    creates = [
        MapEntityMemoryCreate(
            map_id=overworld_map.id,
            entity_id=entity_id,
            entity_type=MapEntityType.SPRITE,
        )
        for entity_id in sorted(new_sprite_ids)
    ]
    creates.extend(
        MapEntityMemoryCreate(
            map_id=overworld_map.id,
            entity_id=entity_id,
            entity_type=MapEntityType.SIGN,
        )
        for entity_id in sorted(new_sign_ids)
    )
    creates.extend(
        MapEntityMemoryCreate(
            map_id=overworld_map.id,
            entity_id=entity_id,
            entity_type=MapEntityType.OBJECT,
        )
        for entity_id in sorted(new_object_ids)
    )
    # Previously seen sprite has been de-rendered. Likely an item that has been picked up, or a
    # scripted character that has walked off the screen. Sprites are the only entity types that can
    # be de-rendered.
    deletes = [
        MapEntityMemoryDelete(
            map_id=overworld_map.id,
            entity_id=entity_id,
            entity_type=MapEntityType.SPRITE,
        )
        for entity_id in sorted(removed_sprite_ids)
    ]
    await apply_map_entity_changes(creates=creates, deletes=deletes)

    overworld_map.known_sprite_ids.update(new_sprite_ids)
    overworld_map.known_sprite_ids.difference_update(removed_sprite_ids)
    for entity_id in removed_sprite_ids:
        overworld_map.sprite_interactions.pop(entity_id, None)
    overworld_map.known_sign_ids.update(new_sign_ids)
    overworld_map.known_object_ids.update(new_object_ids)


async def _update_overworld_map_terrain(
    iteration: int,
    game_state: GameState,
    overworld_map: OverworldMap,
) -> None:
    """Reveal and persist entity-free terrain from the current screen."""
    terrain_screen = game_state.get_ascii_screen_terrain()
    screen_terrain = terrain_screen.ndarray
    screen = game_state.screen

    top = screen.top
    left = screen.left
    bottom = screen.bottom
    right = screen.right
    height = game_state.map.height
    width = game_state.map.width

    # We have to convert the blockages from screen coordinates to map coordinates before we crop.
    overworld_map.blockages.update(
        {screen.to_map_coords(coord): block for coord, block in terrain_screen.blockages.items()}
    )

    # Crop the screen to the area that's part of the current map.
    if top < 0:
        screen_terrain = screen_terrain[-top:]
        top = 0
    if left < 0:
        screen_terrain = screen_terrain[:, -left:]
        left = 0
    if bottom > height:
        screen_terrain = screen_terrain[: height - bottom]
        bottom = height
    if right > width:
        screen_terrain = screen_terrain[:, : width - right]
        right = width

    terrain = overworld_map.terrain_ndarray.copy()
    terrain[top:bottom, left:right] = screen_terrain
    overworld_map.terrain = terrain.tolist()

    await update_map_terrain(
        MapMemoryCreateUpdate(
            iteration=iteration,
            map_id=overworld_map.id,
            terrain=overworld_map.terrain_str,
            blockages={str(coord): block for coord, block in overworld_map.blockages.items()},
        ),
    )


async def _create_overworld_map_from_game_state(
    iteration: int,
    game_state: GameState,
) -> OverworldMap:
    """Create a new overworld map from the game state."""
    terrain = [
        [AsciiTile.UNSEEN.value] * game_state.map.width for _ in range(game_state.map.height)
    ]
    known_map_ids = frozenset(await get_visited_maps()) | {game_state.map.id}
    warp_memories = await get_warp_memories_for_map(game_state.map.id)
    map_boundaries = await get_map_boundary_memories_for_map(game_state.map.id)
    overworld_map = OverworldMap(
        id=game_state.map.id,
        terrain=terrain,
        blockages={},
        known_sprite_ids=set(),
        sprite_interactions={},
        known_warp_ids={memory.warp_id for memory in warp_memories},
        warp_usage_iterations={
            memory.warp_id: memory.last_used_iteration
            for memory in warp_memories
            if memory.last_used_iteration is not None
        },
        known_map_boundaries=tuple(map_boundaries),
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids=set(),
        object_interactions={},
        known_map_ids=known_map_ids,
        north_connection=game_state.map.north_connection,
        south_connection=game_state.map.south_connection,
        east_connection=game_state.map.east_connection,
        west_connection=game_state.map.west_connection,
    )
    await create_map_memory(
        MapMemoryCreateUpdate(
            iteration=iteration,
            map_id=overworld_map.id,
            terrain=overworld_map.terrain_str,
            blockages={str(coord): block for coord, block in overworld_map.blockages.items()},
        ),
    )
    return overworld_map


async def record_map_entity_interactions(
    iteration: int,
    interactions: tuple[CompletedMapEntityInteraction, ...],
) -> None:
    """Persist the latest completed ROM-text interaction for each map entity."""
    if not interactions:
        return
    try:
        latest_by_target = {interaction.target: interaction for interaction in interactions}
        await update_map_entity_interactions(
            [
                MapEntityMemoryInteractionUpdate(
                    map_id=interaction.target.map_id,
                    entity_id=interaction.target.entity_id,
                    entity_type=interaction.target.entity_type,
                    last_interaction=interaction.text,
                    last_interaction_iteration=iteration,
                )
                for interaction in latest_by_target.values()
            ]
        )
    except Exception as error:  # noqa: BLE001
        logger.opt(exception=error).warning(
            "Map-entity interaction persistence failed; continuing without the latest text."
        )


async def record_warp_usage(
    *,
    iteration: int,
    source_map_id: MapId,
    source_warp_id: int,
    destination_map_id: MapId,
    destination_warp: Warp,
) -> None:
    """Persist one ordinary warp transition on both endpoint records."""
    try:
        source_found = await persist_warp_usage(
            iteration=iteration,
            source_map_id=source_map_id,
            source_warp_id=source_warp_id,
            destination=_create_warp_memory(destination_map_id, destination_warp),
        )
        if not source_found:
            logger.bind(map_id=source_map_id.name, warp_id=source_warp_id).warning(
                "Used source warp was not present in warp memory; continuing."
            )
    except Exception as error:  # noqa: BLE001
        logger.opt(exception=error).warning(
            "Warp usage persistence failed; continuing without the latest timestamps."
        )


async def record_observed_map_boundary(
    *,
    button: Button,
    previous: GameState,
    result: ControlResult,
    current: GameState,
) -> None:
    """Persist a map boundary only when one movement input demonstrably crossed it."""
    try:
        boundaries = _get_observed_map_boundaries(button, previous, result, current)
        if not boundaries:
            return
        await persist_map_boundaries(boundaries)
    except Exception as error:  # noqa: BLE001
        logger.opt(exception=error).warning(
            "Map-boundary recording failed; continuing without the latest crossing."
        )


def _get_observed_map_boundaries(
    button: Button,
    previous: GameState,
    result: ControlResult,
    current: GameState,
) -> tuple[MapBoundaryMemoryCreateUpdate, ...]:
    """Recognize a direct crossing and retain its complete crossable coordinate mapping."""
    direction = _BUTTON_DIRECTIONS.get(button)
    if (
        direction is None
        or result.boundary != ControlBoundary.OVERWORLD_READY
        or previous.map.id == current.map.id
        or previous.map.id in {MapId.OUTSIDE, MapId.UNKNOWN}
        or current.map.id in {MapId.OUTSIDE, MapId.UNKNOWN}
    ):
        return ()

    connection = {
        FacingDirection.UP: previous.map.north_connection,
        FacingDirection.DOWN: previous.map.south_connection,
        FacingDirection.LEFT: previous.map.west_connection,
        FacingDirection.RIGHT: previous.map.east_connection,
    }[direction]
    if (
        connection is None
        or connection.direction != direction
        or connection.destination_map != current.map.id
    ):
        return ()

    source = previous.player.coords
    source_coordinate = (
        source.col if direction in {FacingDirection.UP, FacingDirection.DOWN} else source.row
    )
    on_boundary = {
        FacingDirection.UP: source.row == 0,
        FacingDirection.DOWN: source.row == previous.map.height - 1,
        FacingDirection.LEFT: source.col == 0,
        FacingDirection.RIGHT: source.col == previous.map.width - 1,
    }[direction]
    if (
        not on_boundary
        or source_coordinate not in connection.source_coordinates
        or connection.get_destination(source) != current.player.coords
    ):
        return ()

    can_surf = AsciiTile.WATER in previous.get_hm_tiles()
    if direction in {FacingDirection.UP, FacingDirection.DOWN}:
        row = 0 if direction == FacingDirection.UP else previous.map.height - 1
        source_coords = (Coords(row=row, col=col) for col in connection.source_coordinates)
    else:
        col = 0 if direction == FacingDirection.LEFT else previous.map.width - 1
        source_coords = (Coords(row=row, col=col) for row in connection.source_coordinates)
    return tuple(
        MapBoundaryMemoryCreateUpdate(
            map_id=previous.map.id,
            direction=direction,
            row=candidate.row,
            col=candidate.col,
            destination_map_id=current.map.id,
            destination_row=destination.row,
            destination_col=destination.col,
        )
        for candidate in source_coords
        if candidate == source
        or previous.map.is_connection_crossable(connection, candidate, can_surf=can_surf)
        for destination in (connection.get_destination(candidate),)
    )


def _create_warp_memory(map_id: MapId, warp: Warp) -> WarpMemoryCreateUpdate:
    """Build one persistence record from an observed warp."""
    return WarpMemoryCreateUpdate(
        map_id=map_id,
        warp_id=warp.index,
        row=warp.coords.row,
        col=warp.coords.col,
        destination_map_id=warp.destination,
        destination_warp_id=warp.destination_warp_index,
        activation=warp.activation,
    )


_BUTTON_DIRECTIONS = {
    Button.UP: FacingDirection.UP,
    Button.DOWN: FacingDirection.DOWN,
    Button.LEFT: FacingDirection.LEFT,
    Button.RIGHT: FacingDirection.RIGHT,
}
