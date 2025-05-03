from typing import Self

import numpy as np
from common.constants import (
    CUT_TREE_TILE,
    PIKACHU_TILE,
    SPRITE_TILE,
    WALL_TILE,
    WARP_TILE,
    WATER_TILE,
    GRASS_TILE,
    LEDGE_TILE,
    FREE_TILE,
    PLAYER_TILE,
    PLAYER_OFFSET_Y,
    PLAYER_OFFSET_X,
)
from emulator.schemas import MapState, PlayerState, ScreenState, BattleState


from pyboy import PyBoyMemoryView
from pydantic import BaseModel


class YellowLegacyGameState(BaseModel):
    """A snapshot of the Pokemon Yellow Legacy game state."""

    tick_num: int

    player: PlayerState
    cur_map: MapState
    screen: ScreenState
    battle: BattleState

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView, tick_num: int) -> Self:
        """
        Create a new game state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the game state from.
        :return: A new game state.
        """
        return cls(
            tick_num=tick_num,
            player=PlayerState.from_memory(mem),
            cur_map=MapState.from_memory(mem),
            screen=ScreenState.from_memory(mem),
            battle=BattleState.from_memory(mem),
        )

    def get_ascii_screen(self) -> list[list[str]]:
        """Get an ASCII representation of the current screen."""
        tiles = np.array(self.screen.tiles)
        # Each block on screen is a 2x2 square of tiles.
        blocks = []
        for i in range(0, tiles.shape[0], 2):
            row = []
            for j in range(0, tiles.shape[1], 2):
                b = tiles[i : i + 2, j : j + 2]
                if np.any(b == self.cur_map.water_tile):
                    row.append(WATER_TILE)
                elif np.isin(b, self.cur_map.ledge_tiles).any():
                    row.append(LEDGE_TILE)
                elif np.any(b == self.cur_map.grass_tile):
                    row.append(GRASS_TILE)
                elif b.flatten().tolist() == self.cur_map.cut_tree_tiles:
                    row.append(CUT_TREE_TILE)
                elif not np.isin(b, self.cur_map.walkable_tiles).any():
                    row.append(WALL_TILE)
                else:
                    row.append(FREE_TILE)
            blocks.append(row)
        blocks = np.array(blocks)

        blocks[PLAYER_OFFSET_Y, PLAYER_OFFSET_X] = PLAYER_TILE
        for s in self.cur_map.sprites:
            if not s.is_rendered:
                continue
            if screen_coords := self.screen.get_screen_coords(s.y, s.x):
                blocks[screen_coords[0], screen_coords[1]] = SPRITE_TILE

        pikachu = self.cur_map.pikachu_sprite
        if pikachu.is_rendered:
            if screen_coords := self.screen.get_screen_coords(pikachu.y, pikachu.x):
                blocks[screen_coords[0], screen_coords[1]] = PIKACHU_TILE

        for w in self.cur_map.warps:
            if screen_coords := self.screen.get_screen_coords(w.y, w.x):
                blocks[screen_coords[0], screen_coords[1]] = WARP_TILE

        return blocks.tolist()
