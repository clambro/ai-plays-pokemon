"""Dependencies and mutable state for a text-agent run."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.emulator import YellowLegacyEmulator


@dataclass(slots=True, kw_only=True)
class TextContext:
    """Live dependencies for an actionable text screen."""

    state: AgentState
    emulator: YellowLegacyEmulator
