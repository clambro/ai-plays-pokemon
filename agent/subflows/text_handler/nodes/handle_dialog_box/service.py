"""Business logic for handle dialog box in the text subflow."""

import asyncio
from typing import TYPE_CHECKING

from agent.utils import DialogReader

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
    dialog_reader = DialogReader(emulator)
    game_state = await dialog_reader.observe_current_state()
    dialog_box = game_state.get_dialog_box()
    if not dialog_box:
        # Should never happen if we're in this handler, but just in case we need to bail.
        return rolling_memory

    is_blinking_cursor = True
    is_text_outside_dialog_box = True

    # The blinking cursor means that the dialog box is still scrolling. If there's no cursor
    # and no other text on screen, then the dialog box is done scrolling and we can hit A one
    # last time to close the box.
    while dialog_box and (is_blinking_cursor or not is_text_outside_dialog_box):
        await dialog_reader.advance()
        await asyncio.sleep(0.5)  # Buffer to ensure that no new dialog boxes have opened.

        game_state = await dialog_reader.observe_current_state()
        dialog_box = game_state.get_dialog_box()
        is_blinking_cursor = await dialog_reader.is_cursor_blinking()
        is_text_outside_dialog_box = game_state.is_text_on_screen(ignore_dialog_box=True)

    end_text = "The dialog box is now closed." if not dialog_box else ""
    rolling_memory.add_memory(
        content=f'Onscreen text: "{dialog_reader.text}" {end_text}',
    )
    return rolling_memory
