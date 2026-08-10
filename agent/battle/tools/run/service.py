"""Deterministic battle escape input for the battle agent."""

from typing import TYPE_CHECKING

from agent.battle.tools.errors import BattleActionUnavailableError
from agent.battle.utils import get_cursor_pos_in_fight_menu
from common.enums import BattleType, Button

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


async def run(*, emulator: YellowLegacyEmulator) -> str:
    """Select RUN from the battle menu.

    Args:
        emulator: Running emulator used to navigate the battle menu.

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

    return "Attempted to run away from the battle."
