from typing import Self

import numpy as np
from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_SHAPE
from common.enums import AsciiTiles, BattleType, BlockedDirection
from common.schemas import Coords
from emulator.parsers.battle import Battle, parse_battle_state
from emulator.parsers.inventory import Inventory, parse_inventory
from emulator.parsers.map import Map, parse_map_state
from emulator.parsers.player import Player, parse_player
from emulator.parsers.pokemon import Pokemon, parse_party_pokemon
from emulator.parsers.screen import Screen, parse_screen
from emulator.parsers.sign import Sign, parse_signs
from emulator.parsers.sprite import Sprite, parse_pikachu_sprite, parse_sprites
from emulator.parsers.warp import Warp, parse_warps
from emulator.schemas import AsciiScreenWithEntities, DialogBox


class YellowLegacyGameState(BaseModel):
    """A snapshot of the Pokemon Yellow Legacy game state."""

    player: Player
    party: list[Pokemon]
    inventory: Inventory
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
            party=parse_party_pokemon(mem),
            inventory=parse_inventory(mem),
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
        if self.inventory.items:
            out += "<inventory>\n"
            for i in self.inventory.items:
                out += f"- {i.name} (x{i.quantity})\n"
            out += "</inventory>\n"
        out += "</player_info>"
        return out

    @property
    def battle_info(self) -> str:
        """Get a string representation of the battle state."""
        if not self.battle.is_in_battle:
            return ""
        if self.battle.battle_type == BattleType.OTHER:
            return "<battle_info>You are in a special battle, possibly a cutscene.</battle_info>"

        out = "<battle_info>\n"
        if self.battle.battle_type == BattleType.SAFARI_ZONE:
            out += "You are in a Safari Zone battle.\n"
        elif self.battle.battle_type == BattleType.TRAINER:
            out += "You are in a trainer battle.\n"
        elif self.battle.battle_type == BattleType.WILD:
            out += "You are in a battle against a wild Pokemon.\n"

        if self.battle.player_pokemon and self.battle.battle_type != BattleType.SAFARI_ZONE:
            out += "<player_pokemon>\n"
            out += f"Name: {self.battle.player_pokemon.name}\n"
            out += f"Species: {self.battle.player_pokemon.species}\n"
            out += f"Level: {self.battle.player_pokemon.level}\n"
            out += f"HP: {self.battle.player_pokemon.hp} / {self.battle.player_pokemon.max_hp}\n"
            out += f"Status Ailment: {self.battle.player_pokemon.status}\n"
            out += "<moves>\n"
            for m in self.battle.player_pokemon.moves:
                out += f"- {m.name} (PP: {m.pp})\n"
            out += "</moves>\n"
            out += "</player_pokemon>\n"

        if self.battle.enemy_pokemon:
            out += "<enemy_pokemon>\n"
            out += f"Name: {self.battle.enemy_pokemon.species}\n"
            out += f"Level: {self.battle.enemy_pokemon.level}\n"
            out += f"HP Percentage: {self.battle.enemy_pokemon.hp_pct:.0f}%\n"
            out += f"Status Ailment: {self.battle.enemy_pokemon.status}\n"
            out += "</enemy_pokemon>\n"

        if self.battle.num_enemy_pokemon:
            out += (
                f"The enemy trainer has {self.battle.num_enemy_pokemon} Pokemon remaining, "
                "including the one you're battling.\n"
            )

        out += "</battle_info>"
        return out

    def to_screen_coords(self, coords: Coords) -> Coords | None:
        """
        Convert map coordinates to screen coordinates.

        :param coords: The map coordinates.
        :return: The screen coordinates (y, x) or None if they're off screen.
        """
        if (
            coords.row < self.screen.top
            or coords.row >= self.screen.bottom
            or coords.col < self.screen.left
            or coords.col >= self.screen.right
        ):
            return None
        return coords - (self.screen.top, self.screen.left)

    def get_ascii_screen(self) -> AsciiScreenWithEntities:
        """
        Get an ASCII representation of the current screen, including the onscreen sprites and warp
        points.
        """
        blocks, blockages = self._get_background_blocks()

        on_screen_sprites = []
        for s in self.sprites.values():
            if s.is_rendered and (sc := self.to_screen_coords(s.coords)):
                on_screen_sprites.append(s)
                blocks[sc.row, sc.col] = AsciiTiles.SPRITE

        on_screen_warps = []
        for w in self.warps.values():
            sc = self.to_screen_coords(w.coords)
            # There's a funny edge case with warps where they can be rendered on top of walls and
            # are therefore inaccessible. An example is in map 50, when entering Viridian Forest.
            if sc and blocks[sc.row, sc.col] != AsciiTiles.WALL:
                blocks[sc.row, sc.col] = AsciiTiles.WARP
                on_screen_warps.append(w)

        on_screen_signs = []
        for s in self.signs.values():
            if sc := self.to_screen_coords(s.coords):
                blocks[sc.row, sc.col] = AsciiTiles.SIGN
                on_screen_signs.append(s)

        # The player and Pikachu must be drawn last so they're on top of everything else.
        pikachu = self.pikachu
        if pikachu.is_rendered and (sc := self.to_screen_coords(pikachu.coords)):
            blocks[sc.row, sc.col] = AsciiTiles.PIKACHU

        blocks[PLAYER_OFFSET_Y, PLAYER_OFFSET_X] = AsciiTiles.PLAYER

        return AsciiScreenWithEntities(
            screen=blocks.tolist(),
            blockages=blockages,
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

    def _get_background_blocks(self) -> tuple[np.ndarray, dict[Coords, BlockedDirection]]:
        """
        Get the background blocks on the screen without the entities. Note special cases where
        movement is blocked due to elevation differences.

        :return: A tuple of the blocks and blockages.
        """
        tiles = np.array(self.screen.tiles)
        # Each block on screen is a 2x2 square of tiles.
        blocks = np.full(SCREEN_SHAPE, AsciiTiles.WALL, dtype=AsciiTiles)
        blockages: dict[Coords, BlockedDirection] = {}
        for i in range(0, tiles.shape[0], 2):
            for j in range(0, tiles.shape[1], 2):
                b = tiles[i : i + 2, j : j + 2]
                b_idx = (i // 2, j // 2)
                if self.map.water_tile and np.isin(b, self.map.water_tile).any():
                    blocks[b_idx] = AsciiTiles.WATER
                elif ledge_type := self._get_ledge_type(b):
                    blocks[b_idx] = ledge_type
                elif self.map.grass_tile and b[1, 0] == self.map.grass_tile:
                    # In engine/battle/wild_encounters.asm, grass tiles only check the bottom left.
                    blocks[b_idx] = AsciiTiles.GRASS
                elif b.flatten().tolist() == self.map.cut_tree_tiles:
                    blocks[b_idx] = AsciiTiles.CUT_TREE
                elif (
                    b[1, 0] in self.map.walkable_tiles
                    and not np.isin(b, self.map.special_collision_blocks).any()
                ):
                    # Same bottom-left logic applies here, with special exceptions.
                    blocks[b_idx] = AsciiTiles.FREE

                blockages = self._get_blockage(i, j, tiles, blockages)
        return np.array(blocks), blockages

    def _get_ledge_type(self, block: np.ndarray) -> AsciiTiles | None:
        """
        Check if the block is a ledge.

        A tile is defined as a ledge if at least one row/column follows the pattern of a ledge,
        depending on the orientation of the ledge.

        :param block: The block to check, which is a 2x2 array of tile values.
        :return: The type of ledge, or None if the block is not a ledge.
        """
        if (
            block[:, 0].tolist() in self.map.ledge_tiles_down
            or block[:, 1].tolist() in self.map.ledge_tiles_down
        ):
            return AsciiTiles.LEDGE_DOWN
        if (
            block[0, :].tolist() in self.map.ledge_tiles_left
            or block[1, :].tolist() in self.map.ledge_tiles_left
        ):
            return AsciiTiles.LEDGE_LEFT
        if (
            block[0, :].tolist() in self.map.ledge_tiles_right
            or block[1, :].tolist() in self.map.ledge_tiles_right
        ):
            return AsciiTiles.LEDGE_RIGHT
        return None

    def _get_blockage(
        self,
        i: int,
        j: int,
        tiles: np.ndarray,
        blockages: dict[Coords, BlockedDirection],
    ) -> dict[Coords, BlockedDirection]:
        """
        Get the blockage for a given set of coordinates.

        :param i: The row index of the block.
        :param j: The column index of the block.
        :param tiles: The tiles array.
        :param blockages: The blockages dictionary to update.
        :return: The updated blockages dictionary.
        """
        bi, bj = i // 2, j // 2  # Block indices, as opposed to tile indices.
        block = tiles[i : i + 2, j : j + 2]

        if i - 2 >= 0 and j + 2 < tiles.shape[1]:
            row_above = tiles[i - 1, j : j + 2]
            first_pair = {block[0, 0], row_above[0]}
            second_pair = {block[0, 0], row_above[1]}
            if first_pair in self.map.collision_pairs or second_pair in self.map.collision_pairs:
                blockages[Coords(row=bi, col=bj)] |= BlockedDirection.UP
                blockages[Coords(row=bi - 1, col=bj)] |= BlockedDirection.DOWN
        if i - 2 >= 0 and j - 2 >= 0:
            col_left = tiles[i : i + 2, j - 2]
            first_pair = {block[0, 0], col_left[0]}
            second_pair = {block[1, 0], col_left[1]}
            if first_pair in self.map.collision_pairs or second_pair in self.map.collision_pairs:
                blockages[Coords(row=bi, col=bj)] |= BlockedDirection.LEFT
                blockages[Coords(row=bi, col=bj - 1)] |= BlockedDirection.RIGHT
        return blockages
