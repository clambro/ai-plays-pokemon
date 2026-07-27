"""Business logic for fight tool in the battle subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button

if TYPE_CHECKING:
    from agent.subflows.battle_handler.schemas import FightToolArgs
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from memory.raw_memory import RawMemory


async def fight(
    *,
    iteration: int,
    raw_memory: RawMemory,
    tool_args: FightToolArgs,
    emulator: YellowLegacyEmulator,
) -> RawMemory:
    """Use a move on the enemy."""
    game_state = emulator.get_game_state()
    cursor_pos = get_cursor_pos_in_fight_menu(game_state)
    if cursor_pos is None:
        logger.warning("The fight menu is not open. Skipping.")
        return raw_memory

    # Open the FIGHT menu and update the game state.
    if cursor_pos.col == 1:
        await emulator.press_button(Button.LEFT)
    if cursor_pos.row == 1:
        await emulator.press_button(Button.UP)
    await emulator.press_button(Button.A)
    game_state = emulator.get_game_state()

    cursor_index = _get_move_menu_cursor_index(game_state)
    if cursor_index is None:
        logger.warning("The move menu is not open. Skipping.")
        return raw_memory

    # Use the move.
    idx_diff = cursor_index - tool_args.move_index
    if idx_diff > 0:
        for _ in range(idx_diff):
            await emulator.press_button(Button.UP)
    elif idx_diff < 0:
        for _ in range(-idx_diff):
            await emulator.press_button(Button.DOWN)
    await emulator.press_button(Button.A, wait_for_animation=False)

    raw_memory.add_memory(
        iteration=iteration,
        content=f"Attempted to to use {tool_args.move_name}.",
    )
    return raw_memory


def _get_move_menu_cursor_index(game_state: YellowLegacyGameState) -> int | None:
    """Get the cursor index in the move menu."""
    text = game_state.screen.text
    if text.split("\n")[9][1:6] != "TYPE/":
        return None  # Move menu is not open because the type of the move is not shown.
    if game_state.battle.player_pokemon is None:
        return None  # No active Pokemon. Shouldn't happen.

    for i, move in enumerate(game_state.battle.player_pokemon.moves):
        if f"▶{move.name}" in text:
            return i
    return None
