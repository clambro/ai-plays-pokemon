from typing import Self

import numpy as np
from pyboy import PyBoyMemoryView
from pydantic import BaseModel

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y
from common.enums import AsciiTiles
from emulator.char_map import CHAR_TO_INT_MAP, INT_TO_CHAR_MAP
from emulator.schemas import (
    BattleState,
    DialogBox,
    MapState,
    PlayerState,
    ScreenState,
    Sprite,
    Warp,
)

BLINKING_CURSOR_ID = 0xEE
BLANK_TILE_ID = 0x7F


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

    @property
    def is_player_moving(self) -> bool:
        """Check if the player is moving and not in a battle."""
        return self.player.is_moving and not self.battle.is_in_battle

    @property
    def player_info(self) -> str:
        """Get a string representation of the player's information."""
        out = "<player_info>\n"
        out += f"Current map: {self.cur_map.id.name}\n"
        out += f"Current position (row, column): ({self.player.y}, {self.player.x})\n"
        out += f"Facing direction: {self.player.direction.name}\n"
        out += f"Money: {self.player.money}\n"
        out += "</player_info>"
        return out

    @property
    def is_dialog_box_on_screen(self) -> bool:
        """Check if the dialog box is on the screen by checking for the correct corner tiles."""
        screen = np.array(self.screen.tiles)
        return (
            screen[12, 0] == 121
            and screen[12, -1] == 123
            and screen[17, 0] == 125
            and screen[17, -1] == 126
        )

    def get_ascii_screen(self) -> tuple[np.ndarray, list[Sprite], list[Warp]]:
        """
        Get an ASCII representation of the current screen, including the on-screen sprites and warp
        points.
        """
        tiles = np.array(self.screen.tiles)
        # Each block on screen is a 2x2 square of tiles.
        blocks = []
        for i in range(0, tiles.shape[0], 2):
            row = []
            for j in range(0, tiles.shape[1], 2):
                b = tiles[i : i + 2, j : j + 2]
                if np.any(b == self.cur_map.water_tile):
                    row.append(AsciiTiles.WATER)
                elif np.isin(b, self.cur_map.ledge_tiles).any():
                    row.append(AsciiTiles.LEDGE)
                elif np.any(b == self.cur_map.grass_tile):
                    row.append(AsciiTiles.GRASS)
                elif b.flatten().tolist() == self.cur_map.cut_tree_tiles:
                    row.append(AsciiTiles.CUT_TREE)
                elif not np.isin(b, self.cur_map.walkable_tiles).any():
                    row.append(AsciiTiles.WALL)
                else:
                    row.append(AsciiTiles.FREE)
            blocks.append(row)
        blocks = np.array(blocks)

        blocks[PLAYER_OFFSET_Y, PLAYER_OFFSET_X] = AsciiTiles.PLAYER

        on_screen_sprites = []
        for s in self.cur_map.sprites.values():
            if s.is_rendered and (screen_coords := self.screen.get_screen_coords(s.y, s.x)):
                on_screen_sprites.append(s)
                blocks[screen_coords[0], screen_coords[1]] = AsciiTiles.SPRITE

        pikachu = self.cur_map.pikachu_sprite
        if pikachu.is_rendered:
            if screen_coords := self.screen.get_screen_coords(pikachu.y, pikachu.x):
                blocks[screen_coords[0], screen_coords[1]] = AsciiTiles.PIKACHU

        on_screen_warps = []
        for w in self.cur_map.warps.values():
            if screen_coords := self.screen.get_screen_coords(w.y, w.x):
                blocks[screen_coords[0], screen_coords[1]] = AsciiTiles.WARP
                on_screen_warps.append(w)

        return blocks, on_screen_sprites, on_screen_warps

    def is_text_on_screen(self, ignore_dialog_box: bool = False) -> bool:
        """Check if there is text on the screen."""
        a_upper = CHAR_TO_INT_MAP["A"]
        z_upper = CHAR_TO_INT_MAP["Z"]
        a_lower = CHAR_TO_INT_MAP["a"]
        z_lower = CHAR_TO_INT_MAP["z"]
        letters = np.array(list(range(a_upper, z_upper + 1)) + list(range(a_lower, z_lower + 1)))

        tiles = np.array(self.screen.tiles)
        if ignore_dialog_box:
            tiles = tiles[:13, :]

        return np.isin(tiles, letters).sum() > 3  # Avoid false positives caused by weird tilemaps.

    def get_screen_without_blinking_cursor(self) -> np.ndarray:
        """Get the screen without the blinking cursor."""
        tiles = np.array(self.screen.tiles)
        tiles[tiles == BLINKING_CURSOR_ID] = BLANK_TILE_ID
        return tiles.tolist()

    def get_dialog_box(self) -> DialogBox | None:
        """Get the text in the dialog box. Return the top and bottom lines."""
        if not self.is_dialog_box_on_screen:
            return None
        tiles = np.array(self.screen.tiles)
        top_line = "".join(INT_TO_CHAR_MAP.get(t, "") for t in tiles[14, 1:-2])
        bottom_line = "".join(INT_TO_CHAR_MAP.get(t, "") for t in tiles[16, 1:-2])
        cursor_on_screen = tiles[16, -2] == BLINKING_CURSOR_ID
        return DialogBox(
            top_line=top_line.strip(),
            bottom_line=bottom_line.strip(),
            cursor_on_screen=cursor_on_screen,
        )
