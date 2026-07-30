"""Dependencies and mutable state for one overworld-agent run."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.subflows.overworld_handler.state import OverworldHandlerState
    from emulator.emulator import YellowLegacyEmulator


@dataclass(slots=True, kw_only=True)
class OverworldContext:
    """Live dependencies for one overworld decision and action."""

    state: OverworldHandlerState
    emulator: YellowLegacyEmulator
