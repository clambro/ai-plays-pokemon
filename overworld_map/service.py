"""Persistence and updates for the explored overworld map."""

from typing import TYPE_CHECKING

from loguru import logger

from common.enums import AsciiTile, Button, MapEntityType, MapId, WarpActivation
from database.map_entity_memory.repository import (
    apply_map_entity_changes,
    get_map_entity_memories_for_map,
    update_map_entity_interactions,
    update_warp_usage,
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
from database.route_memory.repository import create_route_transition
from database.route_memory.schemas import RouteTransitionCreate
from emulator.control_events import ControlBoundary
from overworld_map.schemas import MapEntityInteractionMemory, OverworldMap

if TYPE_CHECKING:
    from emulator.control_events import ControlResult
    from emulator.game_state import GameState
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
        known_warp_ids={
            memory.entity_id
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.WARP
        },
        warp_usage_iterations={
            memory.entity_id: memory.last_interaction_iteration
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.WARP
            and memory.last_interaction_iteration is not None
        },
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
        await _add_remove_map_entities(game_state, overworld_map)
        await _update_overworld_map_terrain(iteration, game_state, overworld_map)


async def _add_remove_map_entities(
    game_state: GameState,
    overworld_map: OverworldMap,
) -> None:
    """Add or remove entities from the overworld map depending on the current screen."""
    if overworld_map.id != game_state.map.id:
        raise ValueError("Overworld map does not match current game state.")

    ascii_screen = game_state.get_ascii_screen()

    new_sprite_ids = {
        sprite.index
        for sprite in ascii_screen.sprites
        if sprite.is_rendered and sprite.index not in overworld_map.known_sprite_ids
    }
    new_warp_ids = {
        warp.index for warp in ascii_screen.warps if warp.index not in overworld_map.known_warp_ids
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
            entity_type=MapEntityType.WARP,
        )
        for entity_id in sorted(new_warp_ids)
    )
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
    overworld_map.known_warp_ids.update(new_warp_ids)


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
    map_entity_memories = await get_map_entity_memories_for_map(game_state.map.id)
    overworld_map = OverworldMap(
        id=game_state.map.id,
        terrain=terrain,
        blockages={},
        known_sprite_ids=set(),
        sprite_interactions={},
        known_warp_ids={
            memory.entity_id
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.WARP
        },
        warp_usage_iterations={
            memory.entity_id: memory.last_interaction_iteration
            for memory in map_entity_memories
            if memory.entity_type == MapEntityType.WARP
            and memory.last_interaction_iteration is not None
        },
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
    source_warp_index: int,
    destination_map_id: MapId,
    destination_warp_index: int,
) -> None:
    """Persist one ordinary warp transition on both endpoint records."""
    try:
        await update_warp_usage(
            iteration,
            (
                (source_map_id, source_warp_index),
                (destination_map_id, destination_warp_index),
            ),
        )
    except Exception as error:  # noqa: BLE001
        logger.opt(exception=error).warning(
            "Warp usage persistence failed; continuing without the latest timestamps."
        )


async def record_observed_route_transition(
    *,
    iteration: int,
    button: Button,
    previous: GameState,
    result: ControlResult,
    current: GameState,
) -> None:
    """Persist a transition only when one external movement input directly caused it."""
    if (
        button not in _BUTTON_OFFSETS
        or result.boundary != ControlBoundary.OVERWORLD_READY
        or MapId.UNKNOWN in (previous.map.id, current.map.id)
        or (previous.map.id, previous.player.coords) == (current.map.id, current.player.coords)
        or not (
            _is_ordinary_warp_transition(button, previous, current)
            or _is_cardinal_transition(button, previous, current)
        )
    ):
        return

    try:
        await create_route_transition(
            iteration,
            RouteTransitionCreate(
                source_map_id=previous.map.id,
                source_coords=previous.player.coords,
                button=button,
                destination_map_id=current.map.id,
                destination_coords=current.player.coords,
            ),
        )
    except Exception as error:  # noqa: BLE001
        logger.opt(exception=error).warning(
            "Route-memory persistence failed; continuing without the latest observed route."
        )


def _is_ordinary_warp_transition(
    button: Button,
    previous: GameState,
    current: GameState,
) -> bool:
    """Return whether the input activated the ROM-identified ordinary warp."""
    transition = current.warp_transition
    source_warp = previous.warps.get(transition.source_warp_index)
    destination_warp = current.warps.get(transition.destination_warp_index)
    if (
        not transition.is_ordinary_warp
        or transition.source_map_id != previous.map.id
        or source_warp is None
        or destination_warp is None
        or source_warp.destination != current.map.id
        or source_warp.destination_warp_index != transition.destination_warp_index
        or destination_warp.coords != current.player.coords
    ):
        return False
    if source_warp.activation == WarpActivation.STEP_ON:
        return source_warp.coords == previous.player.coords + _BUTTON_OFFSETS.get(button, (0, 0))
    return (
        source_warp.coords == previous.player.coords
        and _WARP_ACTIVATION_BUTTONS.get(source_warp.activation) == button
    )


def _is_cardinal_transition(button: Button, previous: GameState, current: GameState) -> bool:
    """Return whether the input crossed the matching loaded map connection."""
    connection = {
        Button.UP: previous.map.north_connection,
        Button.DOWN: previous.map.south_connection,
        Button.LEFT: previous.map.west_connection,
        Button.RIGHT: previous.map.east_connection,
    }.get(button)
    if connection is None or connection.destination_map != current.map.id:
        return False

    source = previous.player.coords
    source_coordinate = source.col if button in {Button.UP, Button.DOWN} else source.row
    on_boundary = {
        Button.UP: source.row == 0,
        Button.DOWN: source.row == previous.map.height - 1,
        Button.LEFT: source.col == 0,
        Button.RIGHT: source.col == previous.map.width - 1,
    }[button]
    return (
        on_boundary
        and source_coordinate in connection.source_coordinates
        and connection.get_destination(source) == current.player.coords
    )


_BUTTON_OFFSETS = {
    Button.UP: (-1, 0),
    Button.DOWN: (1, 0),
    Button.LEFT: (0, -1),
    Button.RIGHT: (0, 1),
}

_WARP_ACTIVATION_BUTTONS = {
    WarpActivation.UP: Button.UP,
    WarpActivation.DOWN: Button.DOWN,
    WarpActivation.LEFT: Button.LEFT,
    WarpActivation.RIGHT: Button.RIGHT,
}
