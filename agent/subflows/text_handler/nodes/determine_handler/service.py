from agent.subflows.text_handler.enums import TextHandler
from emulator.emulator import YellowLegacyEmulator


class DetermineHandlerService:
    """A service that determines the handler to use in the text handler subflow."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator

    async def determine_handler(self) -> TextHandler | None:
        """Determine the handler to use."""
        game_state = self.emulator.get_game_state()
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
