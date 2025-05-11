import asyncio
from datetime import datetime

from loguru import logger

from common.enums import AgentStateHandler
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
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
            logger.warning("No dialogue box found.")
            return AgentStateHandler.TEXT  # Go to the generic text handler.

        text: list[str] = []
        while dialogue_box:
            top_line = dialogue_box.top_line
            bottom_line = dialogue_box.bottom_line
            # Handle the case where the current top line is the same as the previous bottom line
            # due to the dialogue box scrolling the text up.
            if not text or (top_line and top_line != text[-1]):
                text.append(top_line)
            if not text or (bottom_line and bottom_line != text[-1]):
                text.append(bottom_line)

            counter = 0
            blink_wait_time = 0.1
            max_counter = 5  # Cursor blinks every half second.
            while counter < max_counter:
                logger.warning("Cursor not on screen. Waiting for it to blink.")
                await asyncio.sleep(blink_wait_time)
                game_state = await self.emulator.get_game_state()
                dialogue_box = game_state.get_dialogue_box()
                if dialogue_box and dialogue_box.cursor_on_screen:
                    logger.warning("Cursor is on screen. Breaking.")
                    break
                counter += 1

            if counter == max_counter:
                logger.warning(f"Cursor not on screen after {max_counter} attempts. Breaking.")
                break

            logger.warning("Pressing A to continue dialogue.")
            await self.emulator.press_buttons([Button.A])
            await asyncio.sleep(0.2)
            logger.warning("Button pressed. Waiting for animation to finish.")
            await self.emulator.wait_for_animation_to_finish()
            game_state = await self.emulator.get_game_state()
            dialogue_box = game_state.get_dialogue_box()

        # TODO: Check if there's text outside the dialogue box. If there isn't, hit A one more time.
        # to end the dialogue.

        joined_text = " ".join(text)
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                timestamp=datetime.now(),
                content=f'The following text was read from the main dialogue box: "{joined_text}"',
            )
        )
        if dialogue_box:
            return AgentStateHandler.TEXT  # More work to do. Pass to the generic text handler.
        else:
            return  # Dialogue box is gone, so go to the next agent loop.
