from typing import Self

import numpy as np
from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y
from common.enums import AsciiTiles
from emulator.parsers.battle import Battle, parse_battle_state
from emulator.parsers.map import Map, parse_map_state
from emulator.parsers.player import Player, parse_player
from emulator.parsers.pokemon import Pokemon, parse_player_pokemon
from emulator.parsers.screen import Screen, parse_screen
from emulator.parsers.sign import Sign, parse_signs
from emulator.parsers.sprite import Sprite, parse_pikachu_sprite, parse_sprites
from emulator.parsers.warp import Warp, parse_warps
from emulator.schemas import AsciiScreenWithEntities, DialogBox


class YellowLegacyGameState(BaseModel):
    """A snapshot of the Pokemon Yellow Legacy game state."""

    player: Player
    party: list[Pokemon]
    map: Map
    sprites: dict[int, Sprite]
    pikachu: Sprite
    warps: dict[int, Warp]
    signs: dict[int, Sign]
    screen: Screen
    battle: Battle

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new game state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the game state from.
        :return: A new game state.
        """
        return cls(
            player=parse_player(mem),
            party=parse_player_pokemon(mem),
            map=parse_map_state(mem),
            sprites=parse_sprites(mem),
            pikachu=parse_pikachu_sprite(mem),
            warps=parse_warps(mem),
            signs=parse_signs(mem),
            screen=parse_screen(mem),
            battle=parse_battle_state(mem),
        )

    @property
    def player_info(self) -> str:
        """Get a string representation of the player's information."""
        out = "<player_info>\n"
        if self.player.name:
            out += f"Name: {self.player.name}\n"
        out += f"Money: {self.player.money}\n"
        if self.player.badges:
            out += f"Badges Earned: {', '.join(self.player.badges)}\n"
        out += f"Current Level Cap: {self.player.level_cap}\n"
        if self.party:
            out += "<party>\n"
            for i, p in enumerate(self.party, start=1):
                out += f"<pokemon_{i}>\n"
                out += f"Name: {p.name}\n"
                out += f"Species: {p.species}\n"
                if p.type2:
                    out += f"Type: {p.type1} / {p.type2}\n"
                else:
                    out += f"Type: {p.type1}\n"
                out += f"Level: {p.level}\n"
                out += f"HP: {p.hp} / {p.max_hp}\n"
                out += f"Status Ailment: {p.status}\n"
                out += "<moves>\n"
                for m in p.moves:
                    out += f"- {m.name} (PP: {m.pp})\n"
                out += "</moves>\n"
                out += f"</pokemon_{i}>\n"
            out += "</party>\n"
        out += "</player_info>"
        return out

    def to_screen_coords(self, y: int, x: int) -> tuple[int, int] | None:
        """
        Convert map coordinates to screen coordinates.

        :param y: The map y coordinate.
        :param x: The map x coordinate.
        :return: The screen coordinates (y, x) or None if they're off screen.
        """
        if (
            y < self.screen.top
            or y >= self.screen.bottom
            or x < self.screen.left
            or x >= self.screen.right
        ):
            return None
        return (y - self.screen.top, x - self.screen.left)

    def get_ascii_screen(self) -> AsciiScreenWithEntities:
        """
        Get an ASCII representation of the current screen, including the onscreen sprites and warp
        points.
        """
        blocks = self._get_background_blocks()
        blocks[PLAYER_OFFSET_Y, PLAYER_OFFSET_X] = AsciiTiles.PLAYER

        on_screen_sprites = []
        for s in self.sprites.values():
            if s.is_rendered and (screen_coords := self.to_screen_coords(s.y, s.x)):
                on_screen_sprites.append(s)
                blocks[screen_coords[0], screen_coords[1]] = AsciiTiles.SPRITE

        pikachu = self.pikachu
        if pikachu.is_rendered and (screen_coords := self.to_screen_coords(pikachu.y, pikachu.x)):
            blocks[screen_coords[0], screen_coords[1]] = AsciiTiles.PIKACHU

        on_screen_warps = []
        for w in self.warps.values():
            if screen_coords := self.to_screen_coords(w.y, w.x):
                blocks[screen_coords[0], screen_coords[1]] = AsciiTiles.WARP
                on_screen_warps.append(w)

        on_screen_signs = []
        for s in self.signs.values():
            if screen_coords := self.to_screen_coords(s.y, s.x):
                blocks[screen_coords[0], screen_coords[1]] = AsciiTiles.SIGN
                on_screen_signs.append(s)

        return AsciiScreenWithEntities(
            screen=blocks.tolist(),
            sprites=on_screen_sprites,
            warps=on_screen_warps,
            signs=on_screen_signs,
        )

    def is_text_on_screen(self, *, ignore_dialog_box: bool = False) -> bool:
        """Check if there is text on the screen."""
        text = self.screen.text
        if ignore_dialog_box:
            text = "\n".join(text.split("\n")[:13])
        return len(text.strip()) > 0

    def get_dialog_box(self) -> DialogBox | None:
        """Get the text in the dialog box. Return the top and bottom lines."""
        if not self.screen.is_dialog_box_on_screen:
            return None
        lines = self.screen.text.split("\n")
        return DialogBox(
            top_line=lines[14][1:-2].strip(),
            bottom_line=lines[16][1:-2].strip(),
            has_cursor=lines[16][-2] == "▼",
        )

    def _get_background_blocks(self) -> np.ndarray:
        """Get the background blocks on the screen without the entities."""
        tiles = np.array(self.screen.tiles)
        # Each block on screen is a 2x2 square of tiles.
        blocks = []
        for i in range(0, tiles.shape[0], 2):
            row = []
            for j in range(0, tiles.shape[1], 2):
                b = tiles[i : i + 2, j : j + 2]
                if np.any(b == self.map.water_tile):
                    row.append(AsciiTiles.WATER)
                elif np.isin(b, self.map.ledge_tiles).any():
                    row.append(AsciiTiles.LEDGE)
                elif np.any(b == self.map.grass_tile):
                    row.append(AsciiTiles.GRASS)
                elif b.flatten().tolist() == self.map.cut_tree_tiles:
                    row.append(AsciiTiles.CUT_TREE)
                elif not np.isin(b, self.map.walkable_tiles).any():
                    row.append(AsciiTiles.WALL)
                else:
                    row.append(AsciiTiles.FREE)
            blocks.append(row)
        return np.array(blocks)
