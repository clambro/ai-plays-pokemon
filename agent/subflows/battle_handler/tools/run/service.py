"""Deterministic battle escape input for the battle agent."""

from typing import TYPE_CHECKING

from agent.subflows.battle_handler.tools.errors import BattleActionUnavailableError
from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import BattleType, Button

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from memory.rolling_memory import RollingMemory


async def run(
    *,
    rolling_memory: RollingMemory,
    emulator: YellowLegacyEmulator,
    reason: str,
) -> str:
    """Select RUN from the battle menu.

    Args:
        rolling_memory: Recent memory to update after selecting RUN.
        emulator: Running emulator used to navigate the battle menu.
        reason: Brief explanation of the escape attempt.

    Returns:
        Confirmation of the escape attempt.

    Raises:
        BattleActionUnavailableError: The current battle cannot be escaped.
    """
    game_state = await emulator.get_game_state()
    cursor_pos = get_cursor_pos_in_fight_menu(game_state)
    if cursor_pos is None:
        raise BattleActionUnavailableError("The fight menu is not open.")
    if game_state.battle.battle_type != BattleType.WILD:
        raise BattleActionUnavailableError("Running is only available in a wild battle.")

    if cursor_pos.col == 0:
        await emulator.press_button(Button.RIGHT)
    if cursor_pos.row == 0:
        await emulator.press_button(Button.DOWN)
    await emulator.press_button(Button.A, wait_for_animation=False)

    result = "Attempted to run away from the battle."
    rolling_memory.add_memory(content=f"{reason} {result}")
    return result
