"""Business logic for run tool in the battle subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from memory.raw_memory import RawMemory


async def run_away(
    *,
    iteration: int,
    raw_memory: RawMemory,
    emulator: YellowLegacyEmulator,
) -> RawMemory:
    """Run away from the battle."""
    game_state = emulator.get_game_state()
    cursor_pos = get_cursor_pos_in_fight_menu(game_state)
    if cursor_pos is None:
        logger.warning("The fight menu is not open. Skipping.")
        return raw_memory

    if cursor_pos.col == 0:
        await emulator.press_button(Button.RIGHT)
    if cursor_pos.row == 0:
        await emulator.press_button(Button.DOWN)
    await emulator.press_button(Button.A, wait_for_animation=False)

    raw_memory.add_memory(
        iteration=iteration,
        content="Attempted to run away from the battle.",
    )
    return raw_memory
