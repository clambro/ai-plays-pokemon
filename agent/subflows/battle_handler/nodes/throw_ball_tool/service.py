"""Business logic for throw ball tool in the battle subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button

if TYPE_CHECKING:
    from agent.subflows.battle_handler.schemas import ThrowBallToolArgs
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from memory.rolling_memory import RollingMemory


async def throw_ball(
    *,
    rolling_memory: RollingMemory,
    tool_args: ThrowBallToolArgs,
    emulator: YellowLegacyEmulator,
) -> RollingMemory:
    """Select a Poké Ball from the battle item menu.

    Args:
        rolling_memory: Recent memory to update after selecting the ball.
        tool_args: Inventory index and selected Poké Ball type.
        emulator: Running emulator used to navigate the battle menus.

    Returns:
        The supplied rolling memory, updated when the throw is attempted.
    """
    game_state = await emulator.get_game_state()
    cursor_pos = get_cursor_pos_in_fight_menu(game_state)
    if cursor_pos is None:
        logger.warning("The fight menu is not open. Skipping.")
        return rolling_memory

    # Open the ITEM menu and update the game state.
    if cursor_pos.col == 1:
        await emulator.press_button(Button.LEFT)
    if cursor_pos.row == 0:
        await emulator.press_button(Button.DOWN)
    await emulator.press_button(Button.A)
    game_state = await emulator.get_game_state()

    cursor_index = _get_item_menu_cursor_index(game_state)
    if cursor_index is None:
        logger.warning("The item menu is not open. Skipping.")
        return rolling_memory

    # Throw the ball.
    idx_diff = cursor_index - tool_args.item_index
    if idx_diff > 0:
        for _ in range(idx_diff):
            await emulator.press_button(Button.UP)
    elif idx_diff < 0:
        for _ in range(-idx_diff):
            await emulator.press_button(Button.DOWN)
    await emulator.press_button(Button.A, wait_for_animation=False)

    rolling_memory.add_memory(
        content=f"Attempted to throw a {tool_args.ball}.",
    )
    return rolling_memory


def _get_item_menu_cursor_index(game_state: YellowLegacyGameState) -> int | None:
    """Get the cursor index in the item menu."""
    idx = game_state.screen.menu_item_index + game_state.screen.list_scroll_offset
    if idx >= len(game_state.inventory.items):
        return None
    return idx
