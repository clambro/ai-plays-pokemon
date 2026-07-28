"""Business logic for run tool in the battle subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from memory.rolling_memory import RollingMemory


async def run_away(
    *,
    rolling_memory: RollingMemory,
    emulator: YellowLegacyEmulator,
) -> RollingMemory:
    """Select RUN from the battle menu.

    Args:
        rolling_memory: Recent memory to update after selecting RUN.
        emulator: Running emulator used to navigate the battle menu.

    Returns:
        The supplied rolling memory, updated when the escape attempt is made.
    """
    game_state = await emulator.get_game_state()
    cursor_pos = get_cursor_pos_in_fight_menu(game_state)
    if cursor_pos is None:
        logger.warning("The fight menu is not open. Skipping.")
        return rolling_memory

    if cursor_pos.col == 0:
        await emulator.press_button(Button.RIGHT)
    if cursor_pos.row == 0:
        await emulator.press_button(Button.DOWN)
    await emulator.press_button(Button.A, wait_for_animation=False)

    rolling_memory.add_memory(
        content="Attempted to run away from the battle.",
    )
    return rolling_memory
