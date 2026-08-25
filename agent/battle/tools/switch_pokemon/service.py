"""Deterministic party switching for the battle agent."""

from typing import TYPE_CHECKING

from agent.battle.tools.errors import BattleActionUnavailableError
from agent.battle.tools.utils import get_cursor_pos_in_fight_menu
from common.enums import Button

if TYPE_CHECKING:
    from emulator.emulator import Emulator
    from emulator.game_state import GameState
    from emulator.parsers.pokemon import Pokemon


async def switch_pokemon(
    *,
    emulator: Emulator,
    party_slot: int,
) -> str:
    """Select a party Pokemon from the battle menu.

    Args:
        emulator: Running emulator used to navigate the battle menus.
        party_slot: Zero-based party slot of the Pokemon to switch in.

    Returns:
        Confirmation of the attempted switch.

    Raises:
        BattleActionUnavailableError: The requested Pokemon cannot be switched in.
    """
    game_state = await emulator.get_game_state()
    cursor_pos = get_cursor_pos_in_fight_menu(game_state)
    if cursor_pos is None:
        raise BattleActionUnavailableError("The fight menu is not open.")

    target = _get_available_party_member(game_state, party_slot)
    if target is None:
        raise BattleActionUnavailableError(f"Party slot {party_slot} is not available.")

    if cursor_pos.col == 0:
        await emulator.press_button(Button.RIGHT)
    if cursor_pos.row == 1:
        await emulator.press_button(Button.UP)
    await emulator.press_button(Button.A)
    game_state = await emulator.get_game_state()

    cursor_index = _get_pkmn_menu_cursor_index(game_state)
    if cursor_index is None:
        raise BattleActionUnavailableError("The Pokemon menu did not open.")

    await _move_cursor(emulator, cursor_index, party_slot)
    await emulator.press_button(Button.A)
    game_state = await emulator.get_game_state()

    cursor_index = _get_switch_menu_cursor_index(game_state)
    if cursor_index is None:
        raise BattleActionUnavailableError("The switch menu did not open.")

    await _move_cursor(emulator, cursor_index, 0)
    await emulator.press_button(Button.A)

    return f"Attempted to switch to {target.name} ({target.species})."


def _get_available_party_member(
    game_state: GameState,
    party_slot: int,
) -> Pokemon | None:
    """Resolve a legal party slot against the current battle state."""
    active_party_slot = game_state.battle.active_party_slot
    if active_party_slot is None or party_slot >= len(game_state.party):
        return None

    target = game_state.party[party_slot]
    if target.hp <= 0:
        return None
    if party_slot == active_party_slot:
        return None
    return target


async def _move_cursor(
    emulator: Emulator,
    current_index: int,
    target_index: int,
) -> None:
    """Move a vertical menu cursor to the target index."""
    idx_diff = current_index - target_index
    if idx_diff > 0:
        button = Button.UP
    elif idx_diff < 0:
        button = Button.DOWN
    else:
        return

    for _ in range(abs(idx_diff)):
        await emulator.press_button(button)


def _get_pkmn_menu_cursor_index(game_state: GameState) -> int | None:
    """Get the cursor index in the Pokemon menu."""
    menu_index = game_state.screen.menu_item_index
    if "Choose a POKéMON." not in game_state.screen.text or menu_index >= len(game_state.party):
        return None
    return menu_index


def _get_switch_menu_cursor_index(game_state: GameState) -> int | None:
    """Get the cursor index in the switch menu."""
    text = game_state.screen.text
    if "▶SWITCH" in text:
        return 0
    if "▶STATS" in text:
        return 1
    if "▶CANCEL" in text:
        return 2
    return None
