"""Business logic for determine handler in the text subflow."""

from typing import TYPE_CHECKING

from agent.subflows.text_handler.enums import TextHandler

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


async def determine_handler(emulator: YellowLegacyEmulator) -> TextHandler | None:
    """Determine which text handler matches the visible screen.

    Args:
        emulator: Running emulator used to inspect the current screen.

    Returns:
        The matching text handler, or ``None`` when text is no longer visible.
    """
    game_state = await emulator.get_game_state()
    if not game_state.is_text_on_screen():
        # Should never happen in this handler, but gives us a chance to bail just in case.
        return None

    dialog_box = game_state.get_dialog_box()
    if dialog_box:
        is_text_outside_dialog_box = game_state.is_text_on_screen(ignore_dialog_box=True)
        if is_text_outside_dialog_box:
            return TextHandler.GENERIC  # Usually indicates a menu or a yes/no question.
        return TextHandler.DIALOG_BOX

    if game_state.is_naming_screen():
        return TextHandler.NAME

    return TextHandler.GENERIC
