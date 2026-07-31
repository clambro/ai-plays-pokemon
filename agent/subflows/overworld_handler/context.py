"""Dependencies and mutable state for one overworld-agent run."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from database.long_term_memory.repository import get_all_long_term_memory_titles
from overworld_map.service import prepare_overworld_map

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from overworld_map.schemas import OverworldMap


@dataclass(slots=True, kw_only=True)
class OverworldContext:
    """Live dependencies for one overworld-agent run."""

    state: AgentState
    emulator: YellowLegacyEmulator
    current_map: OverworldMap
    available_long_term_memory_titles: tuple[str, ...]


async def prepare_overworld_context(
    state: AgentState,
    emulator: YellowLegacyEmulator,
    game_state: YellowLegacyGameState,
) -> OverworldContext:
    """Prepare the stable dependencies for one overworld-agent run."""
    current_map = await prepare_overworld_map(state.iteration, game_state)
    titles = await get_all_long_term_memory_titles()
    return OverworldContext(
        state=state,
        emulator=emulator,
        current_map=current_map,
        available_long_term_memory_titles=tuple(sorted(titles)),
    )
