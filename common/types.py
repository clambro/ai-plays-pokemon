"""Shared type aliases and callable definitions."""

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from emulator.game_state import YellowLegacyGameState

type StateStringBuilder = Callable[[YellowLegacyGameState], str]
