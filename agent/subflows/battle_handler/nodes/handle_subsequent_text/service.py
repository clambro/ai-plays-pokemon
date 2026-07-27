"""Business logic for handle subsequent text in the battle subflow."""

from typing import TYPE_CHECKING

from agent.utils import append_dialog_to_list_inplace, is_blinking_cursor_on_screen
from common.enums import Button

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from memory.raw_memory import RawMemory


async def handle_subsequent_text(
    *,
    iteration: int,
    raw_memory: RawMemory,
    emulator: YellowLegacyEmulator,
) -> RawMemory:
    """Read battle dialog produced after an action.

    Args:
        iteration: Current agent iteration used to timestamp captured dialog.
        raw_memory: Recent memory to update with the dialog text.
        emulator: Running emulator used to advance and inspect the dialog box.

    Returns:
        The supplied raw memory after appending any captured dialog.
    """
    text: list[str] = []
    await emulator.wait_for_animation_to_finish()
    while True:
        game_state = emulator.get_game_state()
        dialog_box = game_state.get_dialog_box()
        if not dialog_box:
            break
        append_dialog_to_list_inplace(text, dialog_box)

        if await is_blinking_cursor_on_screen(emulator):
            await emulator.press_button(Button.A)
            continue

        prev_state = game_state
        await emulator.wait_for_animation_to_finish()
        game_state = emulator.get_game_state()
        if game_state.screen.text == prev_state.screen.text:
            break  # Nothing is scrolling, and no animations are happening, so we're done.

    joined_text = " ".join(text).strip()
    if not joined_text:
        return raw_memory

    raw_memory.add_memory(
        iteration=iteration,
        content=f'The following text was read from the battle dialog box: "{joined_text}"',
    )
    return raw_memory
