"""Derived tile views of persistent overworld terrain."""

from typing import TYPE_CHECKING

from common.enums import AsciiTile

if TYPE_CHECKING:
    import numpy as np

    from common.schemas import Coords
    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap


def get_navigation_tiles(current_map: OverworldMap, game_state: GameState) -> np.ndarray:
    """Build traversability from terrain and current blocking entities."""
    tiles = current_map.terrain_ndarray.copy()

    for entity_id in current_map.known_sprite_ids:
        sprite = game_state.sprites.get(entity_id)
        if sprite is not None and sprite.is_rendered and _contains(tiles, sprite.coords):
            tiles[sprite.coords.row, sprite.coords.col] = AsciiTile.SPRITE

    for entity_id in current_map.known_warp_ids:
        warp = game_state.warps.get(entity_id)
        if (
            warp is not None
            and _contains(tiles, warp.coords)
            and tiles[warp.coords.row, warp.coords.col] != AsciiTile.WALL
        ):
            tiles[warp.coords.row, warp.coords.col] = AsciiTile.WARP

    for entity_id in current_map.known_sign_ids:
        sign = game_state.signs.get(entity_id)
        if sign is not None and _contains(tiles, sign.coords):
            tiles[sign.coords.row, sign.coords.col] = AsciiTile.SIGN

    return tiles


def get_current_map_tiles(current_map: OverworldMap, game_state: GameState) -> np.ndarray:
    """Compose the current player and visible entities over explored terrain."""
    tiles = get_navigation_tiles(current_map, game_state)

    if game_state.pikachu.is_rendered and _contains(tiles, game_state.pikachu.coords):
        tiles[game_state.pikachu.coords.row, game_state.pikachu.coords.col] = AsciiTile.PIKACHU

    if _contains(tiles, game_state.player.coords):
        tiles[game_state.player.coords.row, game_state.player.coords.col] = AsciiTile.PLAYER

    return tiles


def _contains(tiles: np.ndarray, coords: Coords) -> bool:
    """Return whether coordinates fall within a tile array."""
    height, width = tiles.shape
    return 0 <= coords.row < height and 0 <= coords.col < width
