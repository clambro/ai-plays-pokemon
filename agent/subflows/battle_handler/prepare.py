"""Prepare the initial context for a battle-agent run."""

from typing import TYPE_CHECKING

from agent.subflows.battle_handler.context import BattleContext

if TYPE_CHECKING:
    from agent.state import AgentState
    from emulator.emulator import YellowLegacyEmulator


async def prepare_battle_context(
    *,
    state: AgentState,
    emulator: YellowLegacyEmulator,
) -> BattleContext:
    """Capture the battle-entry observation and required dependencies."""
    game_state, screenshot = await emulator.get_game_state_with_screenshot()
    return BattleContext(
        state=state,
        game_state=game_state,
        screenshot=screenshot,
        emulator=emulator,
    )
