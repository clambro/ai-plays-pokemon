import asyncio

from common.enums import Button
from emulator.emulator import YellowLegacyEmulator
from emulator.schemas import DialogBox
from memory.raw_memory import RawMemory, RawMemoryPiece


class HandleSubsequentTextService:
    """Handles reading the subsequent text (if present) after a tool has been used."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.emulator = emulator

    async def handle_subsequent_text(self) -> RawMemory:
        """Handle reading the dialog box."""
        text: list[str] = []
        await self.emulator.wait_for_animation_to_finish()
        while True:
            game_state = self.emulator.get_game_state()
            dialog_box = game_state.get_dialog_box()
            if not dialog_box:
                break
            self._append_dialog_to_list(text, dialog_box)

            if await self._is_blinking_cursor_on_screen():
                await self.emulator.press_button(Button.A)
                continue

            prev_state = game_state
            await self.emulator.wait_for_animation_to_finish()
            await self.emulator.wait_for_animation_to_finish()
            game_state = self.emulator.get_game_state()
            if game_state.screen.text == prev_state.screen.text:
                break  # Nothing is scrolling, and no animations are happening, so we're done.

        joined_text = " ".join(text).strip()
        if not joined_text:
            return self.raw_memory

        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=(
                    f'The following text was read from the battle dialog box: "{joined_text}"'
                ),
            ),
        )
        return self.raw_memory

    @staticmethod
    def _append_dialog_to_list(text: list[str], dialog_box: DialogBox) -> None:
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

    async def _is_blinking_cursor_on_screen(self) -> bool:
        """Check if the blinking cursor is on screen."""
        counter = 0
        blink_wait_time = 0.1
        max_counter = 6  # Cursor blinks on/off a bit more than 2x per second.
        while counter < max_counter:
            await asyncio.sleep(blink_wait_time)
            game_state = self.emulator.get_game_state()
            dialog_box = game_state.get_dialog_box()
            if dialog_box and dialog_box.has_cursor:
                break
            counter += 1
        return counter < max_counter
