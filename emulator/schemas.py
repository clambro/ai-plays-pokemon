from typing import Self

import numpy as np
from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from common.constants import PLAYER_OFFSET_X, PLAYER_OFFSET_Y, SCREEN_HEIGHT, SCREEN_WIDTH
from emulator.char_map import get_text_from_byte_array
from emulator.enums import (
    BadgeId,
    FacingDirection,
    PokemonMoveId,
    PokemonSpecies,
    PokemonStatus,
    PokemonType,
)
from emulator.parsers.sign import Sign
from emulator.parsers.sprite import Sprite
from emulator.parsers.warp import Warp


class PokemonMove(BaseModel):
    """A move that a pokemon can learn."""

    id: PokemonMoveId
    pp: int

    model_config = ConfigDict(frozen=True)


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

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView, index: int) -> Self:
        """Create a new player pokemon from a snapshot of the memory."""
        increment = index * 0x2C

        type1 = PokemonType(mem[0xD16F + increment])
        type2 = PokemonType(mem[0xD170 + increment])
        type2 = type2 if type1 != type2 else None  # Monotype pokemon have the same type for both.

        moves = []
        for i in range(4):
            move = PokemonMoveId(mem[0xD172 + increment + i])
            if move != PokemonMoveId.NO_MOVE:
                moves.append(PokemonMove(id=move, pp=mem[0xD187 + increment + i]))

        hp = (mem[0xD16B + increment] << 8) | mem[0xD16B + increment + 1]
        status = PokemonStatus(mem[0xD16E + increment]) if hp > 0 else PokemonStatus.FAINTED

        return cls(
            name=get_text_from_byte_array(mem[0xD2B4 + 0xB * index : 0xD2B4 + 0xB * index + 0xB]),
            species=PokemonSpecies(mem[0xD16A + increment]),
            type1=type1,
            type2=type2,
            level=mem[0xD18B + increment],
            hp=hp,
            max_hp=(mem[0xD18C + increment] << 8) | mem[0xD18C + increment + 1],
            status=status,
            moves=moves,
        )


class PlayerState(BaseModel):
    """The state of the player character."""

    name: str
    is_moving: bool
    y: int
    x: int
    direction: FacingDirection
    money: int
    party: list[PlayerPokemon]
    badges: list[BadgeId]
    level_cap: int

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_memory(cls, mem: PyBoyMemoryView) -> Self:
        """
        Create a new player state from a snapshot of the memory.

        :param mem: The PyBoyMemoryView instance to create the player state from.
        :return: A new player state.
        """
        name = get_text_from_byte_array(mem[0xD157 : 0xD157 + 0xB])
        if name == "NINTEN":
            name = ""  # This is a hack. It's the default name in memory before you choose a name.

        party = []
        for i in range(mem[0xD162]):
            pokemon = PlayerPokemon.from_memory(mem, i)
            if pokemon.species != PokemonSpecies.NO_POKEMON:
                party.append(pokemon)

        badge_byte = mem[0xD3A3]
        champion_byte = mem[0xD745]

        return cls(
            name=name,
            is_moving=mem[0xC107] + mem[0xC108] != 0,
            y=mem[0xD3AE],
            x=mem[0xD3AF],
            direction=FacingDirection(mem[0xD577]),
            money=cls._read_money(mem),
            party=party,
            badges=BadgeId.from_badge_byte(badge_byte),
            level_cap=BadgeId.get_level_cap(badge_byte, champion_byte),
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


class ScreenState(BaseModel):
    """The state of the screen."""

    top: int
    left: int
    bottom: int
    right: int

    # Each block on screen is a 2x2 square of tiles.
    tiles: list[list[int]]

    cursor_index: int

    model_config = ConfigDict(frozen=True)

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
            cursor_index=mem[0xCC30],
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

    model_config = ConfigDict(frozen=True)

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

    model_config = ConfigDict(frozen=True)


class AsciiScreenWithEntities(BaseModel):
    """An ASCII representation of a screen with entities on it."""

    screen: list[list[str]]
    sprites: list[Sprite]
    warps: list[Warp]
    signs: list[Sign]

    model_config = ConfigDict(frozen=True)

    @property
    def ndarray(self) -> np.ndarray:
        """Convert the screen to a numpy array."""
        return np.asarray(self.screen)
