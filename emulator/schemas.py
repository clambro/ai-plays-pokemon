from typing import Self

import numpy as np
from pyboy import PyBoyMemoryView
from pydantic import BaseModel

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from emulator.enums import (
    FacingDirection,
    MapLocation,
    PokemonMove,
    PokemonSpecies,
    PokemonStatus,
    PokemonType,
)


class PlayerPokemon(BaseModel):
    """The state of a player's pokemon."""

    name: str
    species: PokemonSpecies
    type1: PokemonType
    type2: PokemonType | None
    level: int
    hp: int
    max_hp: int
    status: PokemonStatus
    moves: list[PokemonMove]

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView, index: int) -> Self:
        """Create a new player pokemon from a snapshot of the memory."""
        increment = index * 0x2C

        type1 = PokemonType(mem[0xD16F + increment])
        type2 = PokemonType(mem[0xD170 + increment])
        type2 = type2 if type1 != type2 else None  # Monotype pokemon have the same type for both.

        moves = []
        for i in range(4):
            move = PokemonMove(mem[0xD172 + increment + i])
            if move != PokemonMove.NO_MOVE:
                moves.append(move)

        return cls(
            name="test",
            species=PokemonSpecies(mem[0xD163 + increment]),
            type1=type1,
            type2=type2,
            level=mem[0xD18B + increment],
            hp=mem[0xD16B + increment],
            max_hp=mem[0xD18C + increment],
            status=PokemonStatus(mem[0xD16E + increment]),
            moves=moves,
        )


class PlayerState(BaseModel):
    """The state of the player character."""

    is_moving: bool
    y: int
    x: int
    direction: FacingDirection
    money: int
    party: list[PlayerPokemon]

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new player state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the player state from.
        :return: A new player state.
        """
        is_moving = mem[0xC107] + mem[0xC108] != 0
        num_party_pokemon = mem[0xD162]
        return cls(
            is_moving=is_moving,
            y=mem[0xD3AE],
            x=mem[0xD3AF],
            direction=FacingDirection(mem[0xD577]),
            money=cls._read_money(mem),
            party=[PlayerPokemon.from_memory(mem, i) for i in range(num_party_pokemon)],
        )

    @staticmethod
    def _read_money(mem: PyBoyMemoryView) -> int:
        """
        Read the player's money from the binary coded decimal format.

        :param mem: The PyBoyMemoryView instance to read the money from.
        :return: The player's money.
        """
        m1 = mem[0xD394]
        m2 = mem[0xD395]
        m3 = mem[0xD396]
        return (
            ((m1 >> 4) * 100000)
            + ((m1 & 0xF) * 10000)
            + ((m2 >> 4) * 1000)
            + ((m2 & 0xF) * 100)
            + ((m3 >> 4) * 10)
            + (m3 & 0xF)
        )


class Sprite(BaseModel):
    """A sprite on the current map."""

    index: int
    y: int
    x: int
    is_rendered: bool
    moves_randomly: bool


class Warp(BaseModel):
    """
    A warp on the current map.

    Saving the destination is kinda cheating, but much easier than detecting a warp and going back
    to edit the long term memory.
    """

    index: int
    y: int
    x: int
    destination: MapLocation


class Sign(BaseModel):
    """A sign on the current map."""

    index: int
    y: int
    x: int


class MapConnections(BaseModel):
    """The connections of the current map."""

    north: MapLocation | None
    south: MapLocation | None
    east: MapLocation | None
    west: MapLocation | None

    def __str__(self) -> str:
        """Get a string representation of the map connections."""
        out = ""
        if self.north:
            out += f"The map to the north is {self.north.name}.\n"
        if self.south:
            out += f"The map to the south is {self.south.name}.\n"
        if self.east:
            out += f"The map to the east is {self.east.name}.\n"
        if self.west:
            out += f"The map to the west is {self.west.name}.\n"
        if out:
            return out.strip()
        return (
            "There are no direct connections to other maps on this map. The only way to leave this"
            " map is via warp tiles."
        )


class MapState(BaseModel):
    """The state of the current map."""

    id: MapLocation
    tileset_id: int
    height: int
    width: int
    grass_tile: int
    water_tile: int
    ledge_tiles: list[int]
    cut_tree_tiles: list[int]
    walkable_tiles: list[int]
    sprites: dict[int, Sprite]
    pikachu_sprite: Sprite
    warps: dict[int, Warp]
    signs: dict[int, Sign]
    connections: MapConnections

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new map state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the map state from.
        :return: A new map state.
        """
        tileset_id = mem[0xD3B4]

        # These two were found by inspection.
        ledge_tiles = [54, 55] if tileset_id == 0 else []
        cut_tree_tiles = [45, 46, 61, 62] if tileset_id == 0 else []

        walkable_tile_ptr = mem[0xD57D] | (mem[0xD57E] << 8)
        walkable_tiles = []
        for i in range(0x180):  # Max possible unique tiles.
            if mem[walkable_tile_ptr + i] == 0xFF:  # Memory section is terminated by 0xFF.
                break
            walkable_tiles.append(mem[walkable_tile_ptr + i])

        sprites, pikachu_sprite = cls._get_sprites(mem)
        signs = cls._get_signs(mem)

        connections = MapConnections(
            north=MapLocation(mem[0xD3BE]) if mem[0xD3BE] != 0xFF else None,
            south=MapLocation(mem[0xD3C9]) if mem[0xD3C9] != 0xFF else None,
            east=MapLocation(mem[0xD3DF]) if mem[0xD3DF] != 0xFF else None,
            west=MapLocation(mem[0xD3D4]) if mem[0xD3D4] != 0xFF else None,
        )

        return cls(
            id=MapLocation(mem[0xD3AB]),
            tileset_id=mem[0xD3B4],
            height=mem[0xD571],
            width=mem[0xD572],
            grass_tile=mem[0xD582],
            water_tile=mem[3, 0x68A5],
            ledge_tiles=ledge_tiles,
            cut_tree_tiles=cut_tree_tiles,
            walkable_tiles=walkable_tiles,
            sprites=sprites,
            pikachu_sprite=pikachu_sprite,
            warps=cls._get_warps(mem),
            signs=signs,
            connections=connections,
        )

    @staticmethod
    def _get_sprites(mem: PyBoyMemoryView) -> tuple[dict[int, Sprite], Sprite]:
        """
        Get the list of sprites on the current map from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the sprites from.
        :return: A dictionary of normal sprites, keyed by index, plus the pikachu sprite.
        """
        sprites = {}
        for i in range(0x10, 0xF0, 0x10):  # First sprite is the player.
            if mem[0xC100 + i] == 0:  # No more sprites on this map.
                break
            index = i // 0x10
            sprites[index] = Sprite(
                index=index,
                # Sprite coordinates start counting from 4 for some reason.
                y=mem[0xC204 + i] - 4,
                x=mem[0xC205 + i] - 4,
                is_rendered=mem[0xC102 + i] != 0xFF,
                moves_randomly=mem[0xC206 + i] == 0xFE,
            )

        pikachu_sprite = Sprite(
            index=15,  # Pikachu is always the last sprite if it's on screen.
            y=mem[0xC2F4] - 4,
            x=mem[0xC2F5] - 4,
            is_rendered=mem[0xC1F2] != 0xFF,
            moves_randomly=False,
        )
        return sprites, pikachu_sprite

    @staticmethod
    def _get_warps(mem: PyBoyMemoryView) -> dict[int, Warp]:
        """
        Get the list of warps on the current map from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the warps from.
        :return: A dictionary of warps, keyed by index.
        """
        num_warps = mem[0xD3FB]
        warps = {}
        for i in range(num_warps):
            base = 0xD3FC + 4 * i
            warps[i] = Warp(
                index=i,
                y=mem[base],
                x=mem[base + 1],
                destination=MapLocation(mem[base + 3]),
            )
        return warps

    @staticmethod
    def _get_signs(mem: PyBoyMemoryView) -> dict[int, Sign]:
        """
        Get the list of signs on the current map from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the signs from.
        :return: A dictionary of signs, keyed by index.
        """
        num_signs = mem[0xD4FD]
        signs = {}
        for i in range(num_signs):
            base = 0xD4FE + 2 * i
            signs[i] = Sign(
                index=i,
                y=mem[base],
                x=mem[base + 1],
            )
        return signs


class ScreenState(BaseModel):
    """The state of the screen."""

    top: int
    left: int
    bottom: int
    right: int

    # Each block on screen is a 2x2 square of tiles.
    tiles: list[list[int]]

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new screen state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the screen state from.
        :return: A new screen state.
        """
        player_y = mem[0xD3AE]
        player_x = mem[0xD3AF]

        top = player_y - PLAYER_OFFSET_Y
        left = player_x - PLAYER_OFFSET_X
        bottom = top + SCREEN_HEIGHT
        right = left + SCREEN_WIDTH

        shape = (SCREEN_HEIGHT * 2, SCREEN_WIDTH * 2)
        tiles = np.asarray(mem[0xC3A0:0xC508]).reshape(shape).tolist()

        return cls(
            top=top,
            left=left,
            bottom=bottom,
            right=right,
            tiles=tiles,
        )

    def get_screen_coords(self, y: int, x: int) -> tuple[int, int] | None:
        """
        Convert global coordinates to screen coordinates.

        :param y: The global y coordinate.
        :param x: The global x coordinate.
        :return: The screen coordinates (y, x) or None if they're off screen.
        """
        if y < self.top or y >= self.bottom or x < self.left or x >= self.right:
            return None
        return (y - self.top, x - self.left)


class BattleState(BaseModel):
    """The state of the current battle."""

    is_in_battle: bool

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new battle state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the battle state from.
        :return: A new battle state.
        """
        return cls(is_in_battle=bool(mem[0xD057]))


class DialogBox(BaseModel):
    """The state of the dialog box."""

    top_line: str
    bottom_line: str
    cursor_on_screen: bool


class AsciiScreenWithEntities(BaseModel):
    """An ASCII representation of a screen with entities on it."""

    screen: list[list[str]]
    sprites: list[Sprite]
    warps: list[Warp]
    signs: list[Sign]

    @property
    def ndarray(self) -> np.ndarray:
        """Convert the screen to a numpy array."""
        return np.asarray(self.screen)
