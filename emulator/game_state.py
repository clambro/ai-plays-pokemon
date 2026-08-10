"""Game-state extraction from the running emulator."""

from collections import defaultdict
from typing import TYPE_CHECKING, Self

import numpy as np
from pydantic import BaseModel, ConfigDict

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_SHAPE
from common.enums import AsciiTile, Badge, BattleType, BlockedDirection, MapId
from common.schemas import Coords
from emulator.parsers.battle import Battle, parse_battle_state
from emulator.parsers.inventory import Inventory, parse_inventory
from emulator.parsers.map import Map, parse_map_state
from emulator.parsers.player import Player, parse_player
from emulator.parsers.pokemon import BoxPokemon, Pokemon, parse_party_pokemon, parse_pc_pokemon
from emulator.parsers.screen import Screen, parse_screen
from emulator.parsers.sign import Sign, parse_signs
from emulator.parsers.sprite import Sprite, parse_pikachu_sprite, parse_sprites
from emulator.parsers.warp import Warp, parse_warps
from emulator.schemas import AsciiScreenWithEntities, DialogBox

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView


class GameState(BaseModel):
    """A snapshot of the Pokemon Yellow Legacy game state."""

    player: Player
    party: list[Pokemon]
    pc_pokemon: list[BoxPokemon]
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
        """Create a game-state snapshot from emulator memory.

        Args:
            mem: Current PyBoy memory view.

        Returns:
            An immutable parsed snapshot of the relevant game state.
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
        out += "These are the Pokemon in your party, in their current order.\n"
        out += self._pokemon_list_to_str(self.party)
        out += "</party>\n"
        return out

    @property
    def pc_info(self) -> str:
        """Get a string representation of the PC."""
        if not self.pc_pokemon:
            return ""
        out = "<pc_pokemon>\n"
        out += "Stored in the active PC box, not in the party:\n"
        for pokemon in self.pc_pokemon:
            pokemon_type = f"{pokemon.type1}/{pokemon.type2}" if pokemon.type2 else pokemon.type1
            moves = ", ".join(f"{move.name} ({move.pp} PP)" for move in pokemon.moves)
            out += (
                f"- {pokemon.name} ({pokemon.species}, Level {pokemon.level}, {pokemon_type}): "
                f"{moves}\n"
            )
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
            for slot, move in enumerate(self.battle.player_pokemon.moves):
                disabled = " [DISABLED]" if slot == self.battle.disabled_move_slot else ""
                out += f"- {move.name} (PP: {move.pp}){disabled}\n"
            out += "</moves>\n"
            out += "</player_pokemon>\n"

        if self.battle.enemy_pokemon:
            out += "<enemy_pokemon>\n"
            out += f"Name: {self.battle.enemy_pokemon.name}\n"
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
        """Check whether the naming screen is visible.

        The naming screen has no open dialog box and displays the letter-entry grid.

        Returns:
            Whether the visible screen is the name-entry interface.
        """
        name_first_row = "A B C D E F G H I"
        onscreen_text = self.screen.text.replace("▶", "")  # Ignore the cursor.
        return not self.get_dialog_box() and name_first_row in onscreen_text

    def get_hm_tiles(self) -> list[AsciiTile]:
        """Get the tiles that are accessible using the player's current HMs and movepool."""
        hm_tiles = []
        movepool = [m.name for p in self.party for m in p.moves]
        if "CUT" in movepool and Badge.CASCADEBADGE in self.player.badges:
            hm_tiles.append(AsciiTile.CUT_TREE)
        seafoam_current_blocks_surf = (
            self.map.id == MapId.SEAFOAM_ISLANDS_B4F
            and self.player.coords == Coords(row=11, col=7)
            and not self.map.seafoam_current_slowed
        )
        if (
            "SURF" in movepool
            and Badge.SOULBADGE in self.player.badges
            and not seafoam_current_blocks_surf
        ):
            hm_tiles.append(AsciiTile.WATER)
        return hm_tiles

    def to_screen_coords(self, coords: Coords) -> Coords | None:
        """Convert map coordinates to screen coordinates.

        Args:
            coords: Coordinates on the current map.

        Returns:
            Coordinates relative to the visible screen, or ``None`` when they are offscreen.
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
        """Get an ASCII representation of the current screen.

        The returned screen includes visible sprites, signs, warps, Pikachu, and the player.

        Returns:
            The classified visible screen, its elevation blockages, and rendered entities.
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

        top_line = "".join(self.screen.decoded_tiles[14][1:-1])
        bottom_line = "".join(self.screen.decoded_tiles[16][1:-1])
        has_cursor = bottom_line.endswith("▼")
        if has_cursor:
            bottom_line = bottom_line[:-1]

        return DialogBox(
            top_line=top_line.strip(),
            bottom_line=bottom_line.strip(),
            has_cursor=has_cursor,
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
        """Get background blocks and paired-tile movement restrictions.

        Returns:
            The classified background grid and elevation blockages, excluding map entities.
        """
        tiles = np.array(self.screen.tiles)
        # Each block on screen is a 2x2 square of tiles.
        blocks = np.full(SCREEN_SHAPE, AsciiTile.WALL, dtype=AsciiTile)
        blockages: defaultdict[Coords, BlockedDirection] = defaultdict(lambda: BlockedDirection(0))

        for i in range(0, tiles.shape[0], 2):
            for j in range(0, tiles.shape[1], 2):
                block = tiles[i : i + 2, j : j + 2]
                blocks[i // 2, j // 2] = self._classify_background_block(block)
                blockages = self._get_blockage(i, j, tiles, blockages)

        # Remove the default behaviour so we can query blockages without adding new ones.
        return np.array(blocks), dict(blockages)

    def _classify_background_block(self, block: np.ndarray) -> AsciiTile:
        """Classify a 2x2 block of background tiles."""
        if block[1, 0] in self.map.water_tiles:
            return AsciiTile.WATER
        if ledge_type := self._get_ledge_type(block):
            return ledge_type
        if self.map.grass_tile and block[1, 0] == self.map.grass_tile:
            # In engine/battle/wild_encounters.asm, grass tiles only check the bottom left.
            return AsciiTile.GRASS

        flat_block = tuple(block.flatten().tolist())
        if special_type := self._get_special_background_block_type(flat_block):
            return special_type
        if block[1, 0] in self.map.walkable_tiles:
            # The engine uses the same bottom-left logic for ordinary walkable blocks.
            return AsciiTile.FREE
        return AsciiTile.WALL

    def _get_special_background_block_type(
        self,
        flat_block: tuple[int, int, int, int],
    ) -> AsciiTile | None:
        """Classify a block represented by a special four-tile pattern."""
        special_blocks = (
            (self.map.cut_tree_tiles, AsciiTile.CUT_TREE),
            (self.map.boulder_hole_tiles, AsciiTile.BOULDER_HOLE),
            (self.map.pressure_plate_tiles, AsciiTile.PRESSURE_PLATE),
            (self.map.pc_tiles, AsciiTile.PC_TILE),
        )
        for tile_pattern, tile_type in special_blocks:
            if tile_pattern and flat_block == tile_pattern:
                return tile_type
        return self._get_spinner_type(flat_block)

    def _get_ledge_type(self, block: np.ndarray) -> AsciiTile | None:
        """Check whether a block contains a ledge.

        A tile is defined as a ledge if at least one row/column follows the pattern of a ledge,
        depending on the orientation of the ledge.

        Args:
            block: Two-by-two array of tile values to classify.

        Returns:
            The oriented ledge tile, or ``None`` when the block is not a ledge.
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
        """Update blockages for the block at a pair of tile indices.

        Comparisons for collisions, as elsewhere in Pokemon Yellow, are done using the bottom-left
        tile of each block and the corresponding tile in the block above or to the left.

        Args:
            i: Tile row index of the block's upper-left corner.
            j: Tile column index of the block's upper-left corner.
            tiles: Full visible tile array.
            blockages: Blockage mapping to mutate.

        Returns:
            The mutated blockage mapping.
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
