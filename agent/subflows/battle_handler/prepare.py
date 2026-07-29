"""Prepare fresh context for a battle-agent decision."""

from typing import TYPE_CHECKING

from agent.subflows.battle_handler.context import BattleContext

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from memory.goals import Goals
    from memory.long_term_memory import LongTermMemory
    from memory.rolling_memory import RollingMemory


async def prepare_battle_context(
    *,
    rolling_memory: RollingMemory,
    long_term_memory: LongTermMemory,
    goals: Goals,
    emulator: YellowLegacyEmulator,
) -> BattleContext:
    """Capture the current battle observation and its required dependencies."""
    game_state, screenshot = await emulator.get_game_state_with_screenshot()
    return BattleContext(
        game_state=game_state,
        screenshot=screenshot,
        rolling_memory=rolling_memory,
        long_term_memory=long_term_memory,
        goals=goals,
        emulator=emulator,
    )
