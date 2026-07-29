"""Shared utilities for the agent graph."""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from emulator.schemas import DialogBox


def is_battle_handler_state(game_state: YellowLegacyGameState) -> bool:
    """Determine whether the game state belongs to the battle handler."""
    # The nickname screen after catching a Pokemon is considered a battle state by the game,
    # but we need to route it to the text handler instead.
    return game_state.battle.is_in_battle and not game_state.is_naming_screen()


def append_dialog_to_list_inplace(text: list[str], dialog_box: DialogBox) -> None:
    """Append new dialog lines to a list in place.

    A line already present in either of the two most recent positions is skipped so scrolling
    dialog is not duplicated.

    Args:
        text: Accumulated dialog lines to mutate.
        dialog_box: Current two-line dialog box to append.
    """
    top_line = dialog_box.top_line
    bottom_line = dialog_box.bottom_line
    prev_lines = [
        text[-1] if text else None,
        text[-2] if len(text) > 1 else None,
    ]
    if not text or (top_line and top_line not in prev_lines):
        text.append(top_line)
    if not text or (bottom_line and bottom_line not in prev_lines):
        text.append(bottom_line)


async def is_blinking_cursor_on_screen(emulator: YellowLegacyEmulator) -> bool:
    """Check if the blinking cursor is on screen."""
    counter = 0
    blink_wait_time = 0.1
    max_counter = 6  # Cursor blinks on/off a bit more than 2x per second.
    while counter < max_counter:
        await asyncio.sleep(blink_wait_time)
        game_state = await emulator.get_game_state()
        dialog_box = game_state.get_dialog_box()
        if dialog_box and dialog_box.has_cursor:
            break
        counter += 1
    return counter < max_counter
