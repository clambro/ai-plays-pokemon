"""Business logic for handle dialog box in the text subflow."""

import asyncio
from typing import TYPE_CHECKING

from agent.utils import append_dialog_to_list_inplace, is_blinking_cursor_on_screen
from common.enums import Button

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from memory.rolling_memory import RollingMemory


async def handle_dialog_box(
    *,
    rolling_memory: RollingMemory,
    emulator: YellowLegacyEmulator,
) -> RollingMemory:
    """Advance the main dialog box while capturing its text.

    Args:
        rolling_memory: Recent memory to update with the dialog text.
        emulator: Running emulator used to advance and inspect the dialog box.

    Returns:
        The supplied rolling memory after appending any captured dialog.
    """
    game_state = await emulator.get_game_state()
    dialog_box = game_state.get_dialog_box()
    if not dialog_box:
        # Should never happen if we're in this handler, but just in case we need to bail.
        return rolling_memory

    text: list[str] = []
    is_blinking_cursor = True
    is_text_outside_dialog_box = True

    # The blinking cursor means that the dialog box is still scrolling. If there's no cursor
    # and no other text on screen, then the dialog box is done scrolling and we can hit A one
    # last time to close the box.
    while dialog_box and (is_blinking_cursor or not is_text_outside_dialog_box):
        append_dialog_to_list_inplace(text, dialog_box)
        await emulator.press_button(Button.A)
        await asyncio.sleep(0.5)  # Buffer to ensure that no new dialog boxes have opened.

        game_state = await emulator.get_game_state()
        dialog_box = game_state.get_dialog_box()
        is_blinking_cursor = await is_blinking_cursor_on_screen(emulator)
        is_text_outside_dialog_box = game_state.is_text_on_screen(ignore_dialog_box=True)

    joined_text = " ".join(text)
    end_text = "The dialog box is now closed." if not dialog_box else ""
    rolling_memory.add_memory(
        content=f'The following text was read from the main dialog box: "{joined_text}" {end_text}',
    )
    return rolling_memory
