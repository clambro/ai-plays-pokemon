from typing import Self

import numpy as np
from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict

from emulator.enums import BadgeId, FacingDirection
from emulator.parsers.sign import Sign
from emulator.parsers.sprite import Sprite
from emulator.parsers.utils import get_text_from_byte_array
from emulator.parsers.warp import Warp


class PlayerState(BaseModel):
    """The state of the player character."""

    name: str
    y: int
    x: int
    direction: FacingDirection
    money: int
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

        badge_byte = mem[0xD3A3]
        champion_byte = mem[0xD745]

        return cls(
            name=name,
            y=mem[0xD3AE],
            x=mem[0xD3AF],
            direction=FacingDirection(mem[0xD577]),
            money=cls._read_money(mem),
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


class DialogBox(BaseModel):
    """The state of the dialog box."""

    top_line: str
    bottom_line: str
    has_cursor: bool

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
