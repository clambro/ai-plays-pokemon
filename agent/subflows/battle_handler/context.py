"""Dependencies and mutable state for one battle-agent run."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.emulator import YellowLegacyEmulator


@dataclass(slots=True, kw_only=True)
class BattleContext:
    """Live dependencies for one complete battle."""

    state: AgentState
    emulator: YellowLegacyEmulator
