import asyncio
from datetime import datetime

from loguru import logger

from common.enums import AgentStateHandler
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
from emulator.schemas import DialogueBox
from raw_memory.schemas import RawMemory, RawMemoryPiece


class HandleDialogueBoxService:
    """A service that handles reading the dialogue box if it is present."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        raw_memory: RawMemory,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.raw_memory = raw_memory

    async def handle_dialogue_box(self) -> AgentStateHandler | None:
        """
        Handle reading the dialogue box if it is present.

        :return: The handler to set in the state.
        """
        game_state = await self.emulator.get_game_state()
        dialogue_box = game_state.get_dialogue_box()
        if not dialogue_box:
            return AgentStateHandler.TEXT  # Go to the generic text handler.

        text: list[str] = []
        is_blinking_cursor = True
        is_text_outside_dialogue_box = True

        # The blinking cursor means that the dialogue box is still scrolling. If there's no cursor
        # and no other text on screen, then the dialogue box is done scrolling and we can hit A one
        # last time to close the box.
        while dialogue_box and (is_blinking_cursor or not is_text_outside_dialogue_box):
            self.append_dialogue_to_list(text, dialogue_box)
            await self.emulator.press_buttons([Button.A])
            await self.emulator.wait_for_animation_to_finish()
            await asyncio.sleep(0.5)  # Buffer to ensure that no new dialogue boxes have opened.

            is_blinking_cursor = await self._is_blinking_cursor_on_screen()
            is_text_outside_dialogue_box = game_state.is_text_on_screen(ignore_dialogue_box=True)
            game_state = await self.emulator.get_game_state()
            dialogue_box = game_state.get_dialogue_box()

        joined_text = " ".join(text)
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                timestamp=datetime.now(),
                content=f'The following text was read from the main dialogue box: "{joined_text}"',
            )
        )
        if game_state.is_text_on_screen():
            return AgentStateHandler.TEXT  # More work to do. Pass to the generic text handler.
        else:
            return  # All text is gone, so go to the next agent loop.

    @staticmethod
    def append_dialogue_to_list(text: list[str], dialogue_box: DialogueBox) -> None:
        """
        Append the dialogue box text to the text list in place, accounting for the case where the
        current top line is the same as the previous bottom line due to the dialogue box scrolling
        the text up.

        :param text: The list of text to append to.
        :param dialogue_box: The dialogue box to append.
        """
        top_line = dialogue_box.top_line
        bottom_line = dialogue_box.bottom_line
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
            dialogue_box = game_state.get_dialogue_box()
            if dialogue_box and dialogue_box.cursor_on_screen:
                break
            counter += 1
        return counter < max_counter
