"""Business logic for switch Pokémon tool in the battle subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button

if TYPE_CHECKING:
    from agent.subflows.battle_handler.schemas import SwitchPokemonToolArgs
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from memory.raw_memory import RawMemory


async def switch_pokemon(
    *,
    iteration: int,
    raw_memory: RawMemory,
    tool_args: SwitchPokemonToolArgs,
    emulator: YellowLegacyEmulator,
) -> RawMemory:
    """Switch to a different Pokemon."""
    game_state = emulator.get_game_state()
    cursor_pos = get_cursor_pos_in_fight_menu(game_state)
    if cursor_pos is None:
        logger.warning("The fight menu is not open. Skipping.")
        return raw_memory

    # Open the PKMN menu and update the game state.
    if cursor_pos.col == 0:
        await emulator.press_button(Button.RIGHT)
    if cursor_pos.row == 1:
        await emulator.press_button(Button.UP)
    await emulator.press_button(Button.A)
    game_state = emulator.get_game_state()

    cursor_index = _get_pkmn_menu_cursor_index(game_state)
    if cursor_index is None:
        logger.warning("The Pokemon menu is not open. Skipping.")
        return raw_memory

    # Move the cursor to the Pokemon and update the game state.
    await _move_cursor(emulator, cursor_index, tool_args.party_index)
    await emulator.press_button(Button.A)
    game_state = emulator.get_game_state()

    cursor_index = _get_switch_menu_cursor_index(game_state)
    if cursor_index is None:
        logger.warning("The switch menu is not open. Skipping.")
        return raw_memory

    # Select the Pokemon.
    await _move_cursor(emulator, cursor_index, 0)
    await emulator.press_button(Button.A, wait_for_animation=False)

    raw_memory.add_memory(
        iteration=iteration,
        content=f"Attempted to to switch to {tool_args.name}.",
    )
    return raw_memory


async def _move_cursor(
    emulator: YellowLegacyEmulator,
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


def _get_pkmn_menu_cursor_index(game_state: YellowLegacyGameState) -> int | None:
    """Get the cursor index in the Pokemon menu."""
    menu_idx = game_state.screen.menu_item_index
    if "Choose a POKéMON." not in game_state.screen.text or menu_idx >= len(game_state.party):
        return None
    return menu_idx


def _get_switch_menu_cursor_index(game_state: YellowLegacyGameState) -> int | None:
    """Get the cursor index in the switch menu."""
    text = game_state.screen.text
    if "▶SWITCH" in text:
        return 0
    if "▶STATS" in text:
        return 1
    if "▶CANCEL" in text:
        return 2
    return None
