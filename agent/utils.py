import asyncio

from emulator.emulator import YellowLegacyEmulator
from emulator.schemas import DialogBox


def append_dialog_to_list_inplace(text: list[str], dialog_box: DialogBox) -> None:
    """
    Append the dialog box text to the text list in place, accounting for the case where the
    current top line is the same as the previous bottom line due to the dialog box scrolling
    the text up.

    :param text: The list of text to append to.
    :param dialog_box: The dialog box to append.
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
        game_state = emulator.get_game_state()
        dialog_box = game_state.get_dialog_box()
        if dialog_box and dialog_box.has_cursor:
            break
        counter += 1
    return counter < max_counter
