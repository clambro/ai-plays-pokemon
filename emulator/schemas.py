"""Data models representing parsed emulator state."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from common.enums import BlockedDirection
    from common.schemas import Coords
    from emulator.parsers.sign import Sign
    from emulator.parsers.sprite import Sprite
    from emulator.parsers.warp import Warp


@dataclass(frozen=True, slots=True, kw_only=True)
class AsciiScreenTerrain:
    """An entity-free ASCII terrain observation for the visible screen."""

    screen: list[list[str]]
    blockages: dict[Coords, BlockedDirection]

    def __str__(self) -> str:
        """Return a string representation of the screen."""
        return "\n".join("".join(row) for row in self.screen)

    @property
    def ndarray(self) -> np.ndarray:
        """Convert the screen to a numpy array."""
        return np.asarray(self.screen)


@dataclass(frozen=True, slots=True, kw_only=True)
class AsciiScreenWithEntities(AsciiScreenTerrain):
    """An ASCII representation of a screen with entities on it."""

    sprites: list[Sprite]
    warps: list[Warp]
    signs: list[Sign]
