"""Deterministic Poke Ball selection for the battle agent."""

from typing import TYPE_CHECKING

from agent.battle.tools.errors import BattleActionUnavailableError
from agent.battle.tools.utils import get_cursor_pos_in_fight_menu
from common.enums import BattleType, Button, PokeballItem

if TYPE_CHECKING:
    from common.schemas import Coords
    from emulator.emulator import Emulator
    from emulator.game_state import GameState


async def throw_ball(
    *,
    emulator: Emulator,
    ball_type: PokeballItem,
) -> str:
    """Select a Poke Ball from the battle item menu.

    Args:
        emulator: Running emulator used to navigate the battle menus.
        ball_type: Type of Poke Ball to throw.

    Returns:
        Confirmation of the attempted throw.

    Raises:
        BattleActionUnavailableError: The requested ball cannot be thrown from the current state.
    """
    game_state = await emulator.get_game_state()
    cursor_pos = get_cursor_pos_in_fight_menu(game_state)
    if cursor_pos is None:
        raise BattleActionUnavailableError("The fight menu is not open.")
    if game_state.battle.battle_type != BattleType.WILD:
        raise BattleActionUnavailableError("Poke Balls can only be thrown in a wild battle.")

    item_index = next(
        (
            index
            for index, item in enumerate(game_state.inventory.items)
            if item.name == ball_type.value
        ),
        None,
    )
    if item_index is None:
        raise BattleActionUnavailableError(f"No {ball_type.value} is available.")

    await _open_item_menu(emulator, cursor_pos)
    game_state = await emulator.get_game_state()

    cursor_index = _get_item_menu_cursor_index(game_state)
    if cursor_index is None:
        raise BattleActionUnavailableError("The item menu did not open.")

    await _select_item(emulator, cursor_index, item_index)

    return f"Attempted to throw a {ball_type.value}."


async def _open_item_menu(emulator: Emulator, cursor_pos: Coords) -> None:
    """Move to ITEM and open the item menu."""
    if cursor_pos.col == 1:
        await emulator.press_button(Button.LEFT)
    if cursor_pos.row == 0:
        await emulator.press_button(Button.DOWN)
    await emulator.press_button(Button.A)


async def _select_item(
    emulator: Emulator,
    cursor_index: int,
    item_index: int,
) -> None:
    """Move to the selected inventory item and confirm it."""
    index_difference = cursor_index - item_index
    if index_difference > 0:
        for _ in range(index_difference):
            await emulator.press_button(Button.UP)
    elif index_difference < 0:
        for _ in range(-index_difference):
            await emulator.press_button(Button.DOWN)
    await emulator.pulse_button(Button.A)


def _get_item_menu_cursor_index(game_state: GameState) -> int | None:
    """Get the cursor index in the item menu."""
    index = game_state.screen.menu_item_index + game_state.screen.list_scroll_offset
    if index >= len(game_state.inventory.items):
        return None
    return index
