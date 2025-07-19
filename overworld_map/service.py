import asyncio

from common.enums import AsciiTile, MapEntityType
from database.map_entity_memory.repository import (
    create_map_entity_memory,
    delete_map_entity_memory,
    get_map_entity_memories_for_map,
)
from database.map_entity_memory.schemas import MapEntityMemoryCreate, MapEntityMemoryDelete
from database.map_memory.repository import (
    create_map_memory,
    get_map_memory,
    get_visited_maps,
    update_map_tiles,
)
from database.map_memory.schemas import MapMemoryCreateUpdate
from emulator.game_state import YellowLegacyGameState
from overworld_map.schemas import OverworldMap, OverworldSign, OverworldSprite, OverworldWarp


async def get_overworld_map(iteration: int, game_state: YellowLegacyGameState) -> OverworldMap:
    """
    Get the overworld map from the game state, loading the relevant memories from the database if
    the map is known, otherwise creating a new one.
    """
    map_memory = await get_map_memory(game_state.map.id)
    if map_memory is None:
        return await _create_overworld_map_from_game_state(iteration, game_state)

    map_entity_memories = await get_map_entity_memories_for_map(map_memory.map_id)

    game_sprites = game_state.sprites
    sprites = {
        mem.entity_id: OverworldSprite.from_sprite(game_sprites[mem.entity_id], mem.description)
        for mem in map_entity_memories
        if mem.entity_type == MapEntityType.SPRITE and mem.entity_id in game_sprites
    }

    game_warps = game_state.warps
    visited_maps = await get_visited_maps()
    warps = {
        mem.entity_id: OverworldWarp.from_warp(game_warps[mem.entity_id], visited_maps)
        for mem in map_entity_memories
        if mem.entity_type == MapEntityType.WARP and mem.entity_id in game_warps
    }

    game_signs = game_state.signs
    signs = {
        mem.entity_id: OverworldSign.from_sign(game_signs[mem.entity_id], mem.description)
        for mem in map_entity_memories
        if mem.entity_type == MapEntityType.SIGN and mem.entity_id in game_signs
    }

    return OverworldMap(
        id=map_memory.map_id,
        ascii_tiles=[list(row) for row in map_memory.tiles.split("\n")],
        blockages=map_memory.blockages,
        known_sprites=sprites,
        known_warps=warps,
        known_signs=signs,
        north_connection=game_state.map.north_connection,
        south_connection=game_state.map.south_connection,
        east_connection=game_state.map.east_connection,
        west_connection=game_state.map.west_connection,
    )


async def update_map_with_screen_info(
    iteration: int,
    game_state: YellowLegacyGameState,
    overworld_map: OverworldMap,
) -> OverworldMap:
    """
    Update the overworld map with the current screen info. Double check that there is no text
    on the screen and that the map ID matches the current game state before updating or you'll
    create weird artifacts.
    """
    if not game_state.is_text_on_screen() and overworld_map.id == game_state.map.id:
        await _add_remove_map_entities(iteration, game_state, overworld_map)
        await _update_overworld_map_tiles(iteration, game_state, overworld_map)
    return await get_overworld_map(iteration, game_state)


async def _add_remove_map_entities(
    iteration: int,
    game_state: YellowLegacyGameState,
    overworld_map: OverworldMap,
) -> None:
    """Add or remove entities from the overworld map depending on the current screen."""
    if overworld_map.id != game_state.map.id:
        raise ValueError("Overworld map does not match current game state.")

    ascii_screen = game_state.get_ascii_screen()

    tasks = []
    tasks.extend(
        [
            create_map_entity_memory(
                MapEntityMemoryCreate(
                    iteration=iteration,
                    map_id=overworld_map.id,
                    entity_id=s.index,
                    entity_type=MapEntityType.SPRITE,
                ),
            )
            for s in ascii_screen.sprites
            if s.is_rendered and s.index not in overworld_map.known_sprites
        ]
    )
    tasks.extend(
        [
            create_map_entity_memory(
                MapEntityMemoryCreate(
                    iteration=iteration,
                    map_id=overworld_map.id,
                    entity_id=w.index,
                    entity_type=MapEntityType.WARP,
                ),
            )
            for w in ascii_screen.warps
            if w.index not in overworld_map.known_warps
        ]
    )
    tasks.extend(
        [
            create_map_entity_memory(
                MapEntityMemoryCreate(
                    iteration=iteration,
                    map_id=overworld_map.id,
                    entity_id=s.index,
                    entity_type=MapEntityType.SIGN,
                ),
            )
            for s in ascii_screen.signs
            if s.index not in overworld_map.known_signs
        ]
    )
    # Previously seen sprite has been de-rendered. Likely an item that has been picked up, or a
    # scripted character that has walked off the screen. Sprites are the only entity types that can
    # be de-rendered.
    tasks.extend(
        [
            delete_map_entity_memory(
                MapEntityMemoryDelete(
                    map_id=overworld_map.id,
                    entity_id=s.index,
                    entity_type=MapEntityType.SPRITE,
                ),
            )
            for s in overworld_map.known_sprites.values()
            if game_state.to_screen_coords(s.coords) is not None and not s.is_rendered
        ]
    )
    await asyncio.gather(*tasks)


async def _update_overworld_map_tiles(
    iteration: int,
    game_state: YellowLegacyGameState,
    overworld_map: OverworldMap,
) -> None:
    """Update the overworld map with the current game state, revealing new tiles."""
    ascii_screen_with_entities = game_state.get_ascii_screen()
    ascii_screen = ascii_screen_with_entities.ndarray
    screen = game_state.screen

    top = screen.top
    left = screen.left
    bottom = screen.bottom
    right = screen.right
    height = game_state.map.height
    width = game_state.map.width

    # We have to convert the blockages from screen coordinates to map coordinates before we crop.
    overworld_map.blockages.update(
        {
            coord + (top, left): block  # noqa: RUF005
            for coord, block in ascii_screen_with_entities.blockages.items()
        }
    )

    # Crop the screen to the area that's part of the current map.
    if top < 0:
        ascii_screen = ascii_screen[-top:]
        top = 0
    if left < 0:
        ascii_screen = ascii_screen[:, -left:]
        left = 0
    if bottom > height:
        ascii_screen = ascii_screen[: height - bottom]
        bottom = height
    if right > width:
        ascii_screen = ascii_screen[:, : width - right]
        right = width

    overworld_screen_tiles = overworld_map.ascii_tiles_ndarray
    overworld_screen_tiles[top:bottom, left:right] = ascii_screen
    overworld_map.ascii_tiles = overworld_screen_tiles.tolist()

    await update_map_tiles(
        MapMemoryCreateUpdate(
            iteration=iteration,
            map_id=overworld_map.id,
            tiles=overworld_map.ascii_tiles_str,
            blockages={str(coord): block for coord, block in overworld_map.blockages.items()},
        ),
    )


async def _create_overworld_map_from_game_state(
    iteration: int,
    game_state: YellowLegacyGameState,
) -> OverworldMap:
    """Create a new overworld map from the game state."""
    tiles = [[AsciiTile.UNSEEN.value] * game_state.map.width] * game_state.map.height
    overworld_map = OverworldMap(
        id=game_state.map.id,
        ascii_tiles=tiles,
        blockages={},
        known_sprites={},
        known_warps={},
        known_signs={},
        north_connection=game_state.map.north_connection,
        south_connection=game_state.map.south_connection,
        east_connection=game_state.map.east_connection,
        west_connection=game_state.map.west_connection,
    )
    await create_map_memory(
        MapMemoryCreateUpdate(
            iteration=iteration,
            map_id=overworld_map.id,
            tiles=overworld_map.ascii_tiles_str,
            blockages={str(coord): block for coord, block in overworld_map.blockages.items()},
        ),
    )
    return overworld_map
