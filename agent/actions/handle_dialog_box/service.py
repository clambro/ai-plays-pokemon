import asyncio
from datetime import datetime

from common.enums import AgentStateHandler
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
from emulator.schemas import DialogueBox
from raw_memory.schemas import RawMemory, RawMemoryPiece


class HandleDialogueBoxService:
    """A service that handles reading the dialog box if it is present."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        raw_memory: RawMemory,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.raw_memory = raw_memory

    async def handle_dialog_box(self) -> AgentStateHandler | None:
        """
        Handle reading the dialog box if it is present.

        :return: The handler to set in the state.
        """
        game_state = await self.emulator.get_game_state()
        dialog_box = game_state.get_dialog_box()
        if not dialog_box:
            return AgentStateHandler.TEXT  # Go to the generic text handler.

        text: list[str] = []
        is_blinking_cursor = True
        is_text_outside_dialog_box = True

        # The blinking cursor means that the dialog box is still scrolling. If there's no cursor
        # and no other text on screen, then the dialog box is done scrolling and we can hit A one
        # last time to close the box.
        while dialog_box and (is_blinking_cursor or not is_text_outside_dialog_box):
            self._append_dialog_to_list(text, dialog_box)
            await self.emulator.press_buttons([Button.A])
            await self.emulator.wait_for_animation_to_finish()
            await asyncio.sleep(0.5)  # Buffer to ensure that no new dialog boxes have opened.
            
            game_state = await self.emulator.get_game_state()
            dialog_box = game_state.get_dialog_box()
            is_blinking_cursor = await self._is_blinking_cursor_on_screen()
            is_text_outside_dialog_box = game_state.is_text_on_screen(ignore_dialog_box=True)

        joined_text = " ".join(text)
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                timestamp=datetime.now(),
                content=f'The following text was read from the main dialog box: "{joined_text}"',
            )
        )
        if game_state.is_text_on_screen():
            return AgentStateHandler.TEXT  # More work to do. Pass to the generic text handler.
        else:
            return  # All text is gone, so go to the next agent loop.

    @staticmethod
    def _append_dialog_to_list(text: list[str], dialog_box: DialogueBox) -> None:
        """
        Append the dialog box text to the text list in place, accounting for the case where the
        current top line is the same as the previous bottom line due to the dialog box scrolling
        the text up.

        :param text: The list of text to append to.
        :param dialog_box: The dialog box to append.
        """
        top_line = dialog_box.top_line
        bottom_line = dialog_box.bottom_line
        if not text or (top_line and top_line != text[-1]):
            text.append(top_line)
        if not text or (bottom_line and bottom_line != text[-1]):
            text.append(bottom_line)

    async def _is_blinking_cursor_on_screen(self) -> bool:
        """Check if the blinking cursor is on screen."""
        counter = 0
        blink_wait_time = 0.1
        max_counter = 6  # Cursor blinks on/off a bit more than 2x per second.
        while counter < max_counter:
            await asyncio.sleep(blink_wait_time)
            game_state = await self.emulator.get_game_state()
            dialog_box = game_state.get_dialog_box()
            if dialog_box and dialog_box.cursor_on_screen:
                break
            counter += 1
        return counter < max_counter
