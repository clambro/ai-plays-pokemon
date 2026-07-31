"""Dependencies and mutable state for one overworld-agent run."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.emulator import YellowLegacyEmulator
    from overworld_map.schemas import OverworldMap


@dataclass(slots=True, kw_only=True)
class OverworldContext:
    """Live dependencies for one overworld-agent run."""

    state: AgentState
    emulator: YellowLegacyEmulator
    current_map: OverworldMap
