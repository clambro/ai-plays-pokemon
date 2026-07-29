"""Dependencies and mutable state for a text-agent run."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

    from agent.state import AgentState
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState


@dataclass(slots=True, kw_only=True)
class TextContext:
    """Prepared information and dependencies for an actionable text screen."""

    state: AgentState
    game_state: YellowLegacyGameState
    screenshot: Image.Image
    emulator: YellowLegacyEmulator
