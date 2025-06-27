import asyncio

from agent.utils import append_dialog_to_list_inplace, is_blinking_cursor_on_screen
from common.enums import Button
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory, RawMemoryPiece


class HandleDialogBoxService:
    """A service that handles reading the dialog box if it is present."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.emulator = emulator

    async def handle_dialog_box(self) -> RawMemory:
        """Handle reading the dialog box."""
        game_state = self.emulator.get_game_state()
        dialog_box = game_state.get_dialog_box()
        if not dialog_box:
            # Should never happen if we're in this handler, but just in case we need to bail.
            return self.raw_memory

        text: list[str] = []
        is_blinking_cursor = True
        is_text_outside_dialog_box = True

        # The blinking cursor means that the dialog box is still scrolling. If there's no cursor
        # and no other text on screen, then the dialog box is done scrolling and we can hit A one
        # last time to close the box.
        while dialog_box and (is_blinking_cursor or not is_text_outside_dialog_box):
            append_dialog_to_list_inplace(text, dialog_box)
            await self.emulator.press_button(Button.A)
            await asyncio.sleep(0.5)  # Buffer to ensure that no new dialog boxes have opened.

            game_state = self.emulator.get_game_state()
            dialog_box = game_state.get_dialog_box()
            is_blinking_cursor = await is_blinking_cursor_on_screen(self.emulator)
            is_text_outside_dialog_box = game_state.is_text_on_screen(ignore_dialog_box=True)

        joined_text = " ".join(text)
        end_text = "The dialog box is now closed." if not dialog_box else ""
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=(
                    f'The following text was read from the main dialog box: "{joined_text}"'
                    f" {end_text}"
                ),
            ),
        )
        return self.raw_memory
