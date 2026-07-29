"""Dependencies and prepared state for one battle-agent decision."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from memory.goals import Goals
    from memory.long_term_memory import LongTermMemory
    from memory.rolling_memory import RollingMemory


@dataclass(slots=True, kw_only=True)
class BattleContext:
    """Prepared information and dependencies for one battle decision."""

    game_state: YellowLegacyGameState
    screenshot: Image.Image
    rolling_memory: RollingMemory
    long_term_memory: LongTermMemory
    goals: Goals
    emulator: YellowLegacyEmulator
