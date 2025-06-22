import numpy as np
from pydantic import BaseModel, ConfigDict

from common.enums import BlockedDirection
from emulator.parsers.sign import Sign
from emulator.parsers.sprite import Sprite
from emulator.parsers.warp import Warp


class DialogBox(BaseModel):
    """The state of the dialog box."""

    top_line: str
    bottom_line: str
    has_cursor: bool

    model_config = ConfigDict(frozen=True)


class AsciiScreenWithEntities(BaseModel):
    """An ASCII representation of a screen with entities on it."""

    screen: list[list[str]]
    blockages: list[list[BlockedDirection]]
    sprites: list[Sprite]
    warps: list[Warp]
    signs: list[Sign]

    model_config = ConfigDict(frozen=True)

    @property
    def ndarray(self) -> np.ndarray:
        """Convert the screen to a numpy array."""
        return np.asarray(self.screen)
