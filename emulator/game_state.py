from collections import defaultdict
from typing import Self

import numpy as np
from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_SHAPE
from common.enums import AsciiTile, Badge, BattleType, BlockedDirection
from common.schemas import Coords
from emulator.parsers.battle import Battle, parse_battle_state
from emulator.parsers.inventory import Inventory, parse_inventory
from emulator.parsers.map import Map, parse_map_state
from emulator.parsers.player import Player, parse_player
from emulator.parsers.pokemon import Pokemon, parse_party_pokemon, parse_pc_pokemon
from emulator.parsers.screen import Screen, parse_screen
from emulator.parsers.sign import Sign, parse_signs
from emulator.parsers.sprite import Sprite, parse_pikachu_sprite, parse_sprites
from emulator.parsers.warp import Warp, parse_warps
from emulator.schemas import AsciiScreenWithEntities, DialogBox


class YellowLegacyGameState(BaseModel):
    """A snapshot of the Pokemon Yellow Legacy game state."""

    player: Player
    party: list[Pokemon]
    pc_pokemon: list[Pokemon]
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
            pc_pokemon=parse_pc_pokemon(mem),
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
        out += self.party_info
        if self.inventory.items:
            out += "<inventory>\n"
            for i in self.inventory.items:
                out += f"- {i.name} (x{i.quantity})\n"
            out += "</inventory>\n"
        out += self.pc_info
        out += "</player_info>"
        return out

    @property
    def party_info(self) -> str:
        """Get a string representation of the party."""
        if not self.party:
            return ""
        out = "<party>\n"
        out += self._pokemon_list_to_str(self.party)
        out += "</party>\n"
        return out

    @property
    def pc_info(self) -> str:
        """Get a string representation of the PC."""
        if not self.pc_pokemon:
            return ""
        out = "<pc_pokemon>\n"
        out += "These are the Pokemon in the active PC box. They are NOT in your party.\n"
        out += self._pokemon_list_to_str(self.pc_pokemon)
        out += "</pc_pokemon>\n"
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

    @property
    def can_use_strength(self) -> bool:
        """Check if the player can use the Strength HM."""
        movepool = [m.name for p in self.party for m in p.moves]
        return "STRENGTH" in movepool and Badge.RAINBOWBADGE in self.player.badges

    def is_naming_screen(self) -> bool:
        """
        Check if the current screen is the naming screen, meaning that there is no open dialog box
        and the letters for typing the name are on screen.
        """
        name_first_row = "A B C D E F G H I"
        onscreen_text = self.screen.text.replace("▶", "")  # Ignore the cursor.
        return not self.get_dialog_box() and name_first_row in onscreen_text

    def get_hm_tiles(self) -> list[AsciiTile]:
        """Get the tiles that are accessible using the player's current HMs and movepool."""
        hm_tiles = []
        movepool = [m.name for p in self.party for m in p.moves]
        if "CUT" in movepool and Badge.BOULDERBADGE in self.player.badges:
            hm_tiles.append(AsciiTile.CUT_TREE)
        if "SURF" in movepool and Badge.SOULBADGE in self.player.badges:
            hm_tiles.append(AsciiTile.WATER)
        return hm_tiles

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
                blocks[sc.row, sc.col] = AsciiTile.SPRITE

        on_screen_warps = []
        for w in self.warps.values():
            sc = self.to_screen_coords(w.coords)
            # There's a funny edge case with warps where they can be rendered on top of walls and
            # are therefore inaccessible. An example is in map 50, when entering Viridian Forest.
            if sc and blocks[sc.row, sc.col] != AsciiTile.WALL:
                blocks[sc.row, sc.col] = AsciiTile.WARP
                on_screen_warps.append(w)

        on_screen_signs = []
        for s in self.signs.values():
            if sc := self.to_screen_coords(s.coords):
                blocks[sc.row, sc.col] = AsciiTile.SIGN
                on_screen_signs.append(s)

        # The player and Pikachu must be drawn last so they're on top of everything else.
        pikachu = self.pikachu
        if pikachu.is_rendered and (sc := self.to_screen_coords(pikachu.coords)):
            blocks[sc.row, sc.col] = AsciiTile.PIKACHU

        blocks[PLAYER_OFFSET_Y, PLAYER_OFFSET_X] = AsciiTile.PLAYER

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

    def _pokemon_list_to_str(self, pokemon_list: list[Pokemon]) -> str:
        """Helper function to convert a list of Pokemon to a string."""
        out = ""
        for i, p in enumerate(pokemon_list):
            out += f"<pokemon_{i}>\n"
            out += f"Name: {p.name}\n"
            out += f"Species: {p.species}\n"
            if p.type2:
                out += f"Type: {p.type1} / {p.type2}\n"
            else:
                out += f"Type: {p.type1}\n"
            out += f"Level: {p.level}\n"
            if p.level >= self.player.level_cap:
                out += (
                    "This Pokemon is at the level cap and cannot be leveled up further until the"
                    " level cap is raised.\n"
                )
            out += f"HP: {p.hp} / {p.max_hp}\n"
            out += f"Status Ailment: {p.status}\n"
            out += "<moves>\n"
            for m in p.moves:
                out += f"- {m.name} (PP: {m.pp})\n"
            out += "</moves>\n"
            out += f"</pokemon_{i}>\n"
        return out

    def _get_background_blocks(self) -> tuple[np.ndarray, dict[Coords, BlockedDirection]]:
        """
        Get the background blocks on the screen without the entities. Note special cases where
        movement is blocked due to elevation differences.

        :return: A tuple of the blocks and blockages.
        """
        tiles = np.array(self.screen.tiles)
        # Each block on screen is a 2x2 square of tiles.
        blocks = np.full(SCREEN_SHAPE, AsciiTile.WALL, dtype=AsciiTile)
        blockages: defaultdict[Coords, BlockedDirection] = defaultdict(lambda: BlockedDirection(0))

        for i in range(0, tiles.shape[0], 2):
            for j in range(0, tiles.shape[1], 2):
                b = tiles[i : i + 2, j : j + 2]
                b_flat = tuple(b.flatten().tolist())
                b_idx = (i // 2, j // 2)

                if self.map.water_tile and np.isin(b, self.map.water_tile).any():
                    blocks[b_idx] = AsciiTile.WATER
                elif ledge_type := self._get_ledge_type(b):
                    blocks[b_idx] = ledge_type
                elif self.map.grass_tile and b[1, 0] == self.map.grass_tile:
                    # In engine/battle/wild_encounters.asm, grass tiles only check the bottom left.
                    blocks[b_idx] = AsciiTile.GRASS
                elif self.map.cut_tree_tiles and b_flat == self.map.cut_tree_tiles:
                    blocks[b_idx] = AsciiTile.CUT_TREE
                elif self.map.boulder_hole_tiles and b_flat == self.map.boulder_hole_tiles:
                    blocks[b_idx] = AsciiTile.BOULDER_HOLE
                elif self.map.pressure_plate_tiles and b_flat == self.map.pressure_plate_tiles:
                    blocks[b_idx] = AsciiTile.PRESSURE_PLATE
                elif self.map.pc_tiles and b_flat == self.map.pc_tiles:
                    blocks[b_idx] = AsciiTile.PC_TILE
                elif spinner_type := self._get_spinner_type(b_flat):
                    blocks[b_idx] = spinner_type
                elif b[1, 0] in self.map.walkable_tiles:  # Same bottom-left logic applies here.
                    blocks[b_idx] = AsciiTile.FREE

                blockages = self._get_blockage(i, j, tiles, blockages)

        # Remove the default behaviour so we can query blockages without adding new ones.
        return np.array(blocks), dict(blockages)

    def _get_ledge_type(self, block: np.ndarray) -> AsciiTile | None:
        """
        Check if the block is a ledge.

        A tile is defined as a ledge if at least one row/column follows the pattern of a ledge,
        depending on the orientation of the ledge.

        :param block: The block to check, which is a 2x2 array of tile values.
        :return: The type of ledge, or None if the block is not a ledge.
        """
        top = tuple(block[0, :].tolist())
        bottom = tuple(block[1, :].tolist())
        left = tuple(block[:, 0].tolist())
        right = tuple(block[:, 1].tolist())

        if left in self.map.ledge_tiles_down or right in self.map.ledge_tiles_down:
            return AsciiTile.LEDGE_DOWN
        if top in self.map.ledge_tiles_left or bottom in self.map.ledge_tiles_left:
            return AsciiTile.LEDGE_LEFT
        if top in self.map.ledge_tiles_right or bottom in self.map.ledge_tiles_right:
            return AsciiTile.LEDGE_RIGHT
        return None

    def _get_spinner_type(self, flat_block: tuple[int, int, int, int]) -> AsciiTile | None:
        """Get the type of spinner for a given block."""
        if self.map.spinner_tiles is None:
            return None
        tile = None
        if flat_block == self.map.spinner_tiles.up:
            tile = AsciiTile.SPINNER_UP
        elif flat_block == self.map.spinner_tiles.down:
            tile = AsciiTile.SPINNER_DOWN
        elif flat_block == self.map.spinner_tiles.left:
            tile = AsciiTile.SPINNER_LEFT
        elif flat_block == self.map.spinner_tiles.right:
            tile = AsciiTile.SPINNER_RIGHT
        elif flat_block == self.map.spinner_tiles.stop:
            tile = AsciiTile.SPINNER_STOP
        return tile

    def _get_blockage(
        self,
        i: int,
        j: int,
        tiles: np.ndarray,
        blockages: defaultdict[Coords, BlockedDirection],
    ) -> defaultdict[Coords, BlockedDirection]:
        """
        Get the blockage for a given set of coordinates by checking if the tiles in the bottom-left
        corner of this block and the one above it are in a collision pair.

        Comparisons for collisions, as elsewhere in Pokemon Yellow, are done using the bottom-left
        tile of each block.

        :param i: The tile row index of the upper-left corner of the block.
        :param j: The tile column index of the upper-left corner of the block.
        :param tiles: The tiles array.
        :param blockages: The blockages dictionary to update.
        :return: The updated blockages dictionary.
        """
        bi, bj = i // 2, j // 2  # Block indices, as opposed to tile indices.
        block_tile = tiles[i + 1, j]  # The bottom-left tile of the block is the one used to check.

        if i - 2 >= 0:
            block_above_tile = tiles[i - 1, j]
            pair = {block_tile, block_above_tile}
            if pair in self.map.collision_pairs:
                blockages[Coords(row=bi, col=bj)] |= BlockedDirection.UP
                blockages[Coords(row=bi - 1, col=bj)] |= BlockedDirection.DOWN

        if j - 2 >= 0:
            block_left_tile = tiles[i + 1, j - 2]
            pair = {block_left_tile, block_tile}
            if pair in self.map.collision_pairs:
                blockages[Coords(row=bi, col=bj)] |= BlockedDirection.LEFT
                blockages[Coords(row=bi, col=bj - 1)] |= BlockedDirection.RIGHT

        return blockages
