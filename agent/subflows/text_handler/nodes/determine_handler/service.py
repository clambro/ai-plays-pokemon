from agent.subflows.text_handler.enums import TextHandler
from emulator.emulator import YellowLegacyEmulator


class DetermineHandlerService:
    """A service that determines the handler to use in the text handler subflow."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator

    async def determine_handler(self) -> TextHandler:
        """Determine the handler to use."""
        game_state = self.emulator.get_game_state()
        dialog_box = game_state.get_dialog_box()
        is_text_outside_dialog_box = game_state.is_text_on_screen(ignore_dialog_box=True)
        if dialog_box and not is_text_outside_dialog_box:
            return TextHandler.DIALOG_BOX

        name_first_row = "A B C D E F G H I"
        onscreen_text = game_state.get_onscreen_text()
        if name_first_row in onscreen_text:
            return TextHandler.NAME

        return TextHandler.GENERIC
