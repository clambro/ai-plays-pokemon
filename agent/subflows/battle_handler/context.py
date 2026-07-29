"""Dependencies and mutable state for one battle-agent run."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

    from agent.state import AgentState
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState


@dataclass(slots=True, kw_only=True)
class BattleContext:
    """Prepared information and dependencies for one complete battle."""

    state: AgentState
    game_state: YellowLegacyGameState
    screenshot: Image.Image
    emulator: YellowLegacyEmulator
