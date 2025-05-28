import asyncio

from common.enums import AsciiTiles, MapEntityType
from database.map_entity_memory.repository import (
    create_map_entity_memory,
    get_map_entity_memories_for_map,
)
from database.map_entity_memory.schemas import MapEntityMemoryCreate
from database.map_memory.repository import create_map_memory, get_map_memory, update_map_tiles
from database.map_memory.schemas import MapMemoryCreateUpdate
from database.sprite_memory.repository import (
    create_sprite_memory,
    delete_sprite_memory,
    get_sprite_memories_for_map,
)
from database.sprite_memory.schemas import SpriteMemoryCreate
from emulator.game_state import YellowLegacyGameState
from overworld_map.schemas import OverworldMap, OverworldSign, OverworldSprite, OverworldWarp


async def get_overworld_map(iteration: int, game_state: YellowLegacyGameState) -> OverworldMap:
    """
    Get the overworld map from the game state, loading the relevant memories from the database if
    the map is known, otherwise creating a new one.
    """
    map_memory = await get_map_memory(game_state.cur_map.id)
    if map_memory is None:
        return await _create_overworld_map_from_game_state(iteration, game_state)

    map_entity_memories = await get_map_entity_memories_for_map(map_memory.map_id)

    sprite_memories = await get_sprite_memories_for_map(map_memory.map_id)
    game_sprites = game_state.cur_map.sprites
    sprites = {
        mem.sprite_id: OverworldSprite.from_sprite(game_sprites[mem.sprite_id], mem.description)
        for mem in sprite_memories
    }

    game_warps = game_state.cur_map.warps
    warps = {
        mem.entity_id: OverworldWarp.from_warp(game_warps[mem.entity_id], mem.description)
        for mem in map_entity_memories
        if mem.entity_type == MapEntityType.WARP
    }

    game_signs = game_state.cur_map.signs
    signs = {
        mem.entity_id: OverworldSign.from_sign(game_signs[mem.entity_id], mem.description)
        for mem in map_entity_memories
        if mem.entity_type == MapEntityType.SIGN
    }

    overworld_map = OverworldMap(
        id=map_memory.map_id,
        ascii_tiles=[list(row) for row in map_memory.tiles.split("\n")],
        known_sprites=sprites,
        known_warps=warps,
        known_signs=signs,
        connections=game_state.cur_map.connections,
    )
    return overworld_map


async def update_map_with_screen_info(
    iteration: int,
    game_state: YellowLegacyGameState,
    overworld_map: OverworldMap,
) -> OverworldMap:
    """Update the overworld map with the current screen info."""
    await _add_remove_map_entities(iteration, game_state, overworld_map)
    await _update_overworld_map_tiles(iteration, game_state, overworld_map)
    return await get_overworld_map(iteration, game_state)


async def _add_remove_map_entities(
    iteration: int,
    game_state: YellowLegacyGameState,
    overworld_map: OverworldMap,
) -> None:
    """Add or remove sprites or warps from the overworld map depending on the current screen."""
    if overworld_map.id != game_state.cur_map.id:
        raise ValueError("Overworld map does not match current game state.")

    ascii_screen = game_state.get_ascii_screen()

    tasks = []
    for s in ascii_screen.sprites:
        if s.is_rendered and s.index not in overworld_map.known_sprites:
            tasks.append(
                create_sprite_memory(
                    SpriteMemoryCreate(
                        iteration=iteration,
                        map_id=overworld_map.id,
                        sprite_id=s.index,
                    ),
                ),
            )

    for s in overworld_map.known_sprites.values():
        is_s_on_screen = game_state.screen.get_screen_coords(s.y, s.x) is not None
        if is_s_on_screen and not s.is_rendered:
            # Previously seen sprite has been de-rendered. Likely an item that has been picked up,
            # or a scripted character that has walked off the screen.
            tasks.append(delete_sprite_memory(overworld_map.id, s.index))

    for w in ascii_screen.warps:
        if w.index not in overworld_map.known_warps:
            tasks.append(
                create_map_entity_memory(
                    MapEntityMemoryCreate(
                        iteration=iteration,
                        map_id=overworld_map.id,
                        entity_id=w.index,
                        entity_type=MapEntityType.WARP,
                    ),
                ),
            )
        # Warps are never de-rendered, so no need to delete them.

    for s in ascii_screen.signs:
        if s.index not in overworld_map.known_signs:
            tasks.append(
                create_map_entity_memory(
                    MapEntityMemoryCreate(
                        iteration=iteration,
                        map_id=overworld_map.id,
                        entity_id=s.index,
                        entity_type=MapEntityType.SIGN,
                    ),
                ),
            )
        # Signs are never de-rendered, so no need to delete them.

    await asyncio.gather(*tasks)


async def _update_overworld_map_tiles(
    iteration: int,
    game_state: YellowLegacyGameState,
    overworld_map: OverworldMap,
) -> None:
    """Update the overworld map with the current game state, revealing new tiles."""
    ascii_screen = game_state.get_ascii_screen().ndarray
    screen = game_state.screen

    top = screen.top
    left = screen.left
    bottom = screen.bottom
    right = screen.right
    height = game_state.cur_map.height
    width = game_state.cur_map.width

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

    ascii_tiles = overworld_map.ascii_tiles_ndarray
    ascii_tiles[top:bottom, left:right] = ascii_screen
    overworld_map.ascii_tiles = ascii_tiles.tolist()

    await update_map_tiles(
        MapMemoryCreateUpdate(
            iteration=iteration,
            map_id=overworld_map.id,
            tiles=overworld_map.ascii_tiles_str,
        ),
    )


async def _create_overworld_map_from_game_state(
    iteration: int,
    game_state: YellowLegacyGameState,
) -> OverworldMap:
    """Create a new overworld map from the game state."""
    tiles = []
    for _ in range(game_state.cur_map.height):
        row = []
        for _ in range(game_state.cur_map.width):
            row.append(AsciiTiles.UNSEEN)
        tiles.append(row)
    overworld_map = OverworldMap(
        id=game_state.cur_map.id,
        ascii_tiles=tiles,
        known_sprites={},
        known_warps={},
        known_signs={},
        connections=game_state.cur_map.connections,
    )
    await create_map_memory(
        MapMemoryCreateUpdate(
            iteration=iteration,
            map_id=overworld_map.id,
            tiles=overworld_map.ascii_tiles_str,
        ),
    )
    return overworld_map
