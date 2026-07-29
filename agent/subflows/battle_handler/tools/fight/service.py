"""Deterministic move selection for the battle agent."""

from typing import TYPE_CHECKING

from agent.subflows.battle_handler.tools.errors import BattleActionUnavailableError
from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button

if TYPE_CHECKING:
    from common.schemas import Coords
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState

_STRUGGLE = "STRUGGLE"


async def fight(*, emulator: YellowLegacyEmulator, move_slot: int) -> str:
    """Select a move from the battle menu.

    Args:
        emulator: Running emulator used to navigate the battle menus.
        move_slot: Zero-based slot of the move to use.

    Returns:
        Confirmation of the attempted move.

    Raises:
        BattleActionUnavailableError: The requested move cannot be used from the current state.
    """
    game_state = await emulator.get_game_state()
    cursor_pos = get_cursor_pos_in_fight_menu(game_state)
    if cursor_pos is None:
        raise BattleActionUnavailableError("The fight menu is not open.")

    move_name = _get_available_move_name(game_state, move_slot)
    if move_name is None:
        raise BattleActionUnavailableError(f"Move slot {move_slot} is not available.")

    await _open_move_menu(emulator, cursor_pos)
    if move_name == _STRUGGLE:
        return f"Attempted to use {_STRUGGLE}."

    game_state = await emulator.get_game_state()

    cursor_index = _get_move_menu_cursor_index(game_state)
    if cursor_index is None:
        raise BattleActionUnavailableError("The move menu did not open.")

    await _select_move(emulator, cursor_index, move_slot)

    return f"Attempted to use {move_name}."


def _get_available_move_name(game_state: YellowLegacyGameState, move_slot: int) -> str | None:
    """Resolve a legal move slot against the current battle state."""
    player_pokemon = game_state.battle.player_pokemon
    if player_pokemon is None:
        return None

    available_moves = [
        (slot, move.name)
        for slot, move in enumerate(player_pokemon.moves)
        if move.pp > 0 and slot != game_state.battle.disabled_move_slot
    ]
    if not available_moves:
        return _STRUGGLE if move_slot == 0 else None
    return next((name for slot, name in available_moves if slot == move_slot), None)


async def _open_move_menu(emulator: YellowLegacyEmulator, cursor_pos: Coords) -> None:
    """Move to FIGHT and open the move menu."""
    if cursor_pos.col == 1:
        await emulator.press_button(Button.LEFT)
    if cursor_pos.row == 1:
        await emulator.press_button(Button.UP)
    await emulator.press_button(Button.A)


async def _select_move(
    emulator: YellowLegacyEmulator,
    cursor_index: int,
    move_slot: int,
) -> None:
    """Move to the selected move slot and confirm it."""
    slot_difference = cursor_index - move_slot
    if slot_difference > 0:
        for _ in range(slot_difference):
            await emulator.press_button(Button.UP)
    elif slot_difference < 0:
        for _ in range(-slot_difference):
            await emulator.press_button(Button.DOWN)
    await emulator.press_button(Button.A, wait_for_animation=False)


def _get_move_menu_cursor_index(game_state: YellowLegacyGameState) -> int | None:
    """Get the cursor index in the move menu."""
    text = game_state.screen.text
    # A disabled highlighted move replaces the normal TYPE/PP panel with "Disabled".
    if "TYPE" not in text and "Disabled" not in text:
        return None
    if game_state.battle.player_pokemon is None:
        return None

    for index, move in enumerate(game_state.battle.player_pokemon.moves):
        if f"▶{move.name}" in text:
            return index
    return None
