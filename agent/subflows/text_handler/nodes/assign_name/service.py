import numpy as np

from agent.subflows.text_handler.nodes.assign_name.prompts import GET_NAME_PROMPT
from agent.subflows.text_handler.nodes.assign_name.schemas import NameResponse
from common.constants import GAME_TICKS_PER_SECOND
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
from emulator.game_state import YellowLegacyGameState
from memory.raw_memory import RawMemory, RawMemoryPiece

LETTER_ARR = np.array(
    [
        ["A", "B", "C", "D", "E", "F", "G", "H", "I"],
        ["J", "K", "L", "M", "N", "O", "P", "Q", "R"],
        ["S", "T", "U", "V", "W", "X", "Y", "Z", " "],
    ],
)


class AssignNameService:
    """A service that assigns a name to something in the game."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH_LITE)

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def assign_name(self) -> RawMemory:
        """Assign a name to something in the game."""
        game_state = self.emulator.get_game_state()
        first_name_row = "A B C D E F G H I"
        if first_name_row not in game_state.screen.text:
            # Should never happen if we're in this handler, but just in case we need to bail.
            return self.raw_memory

        try:
            name = await self._get_desired_name(game_state)
            await self._enter_name(name)
        except Exception as e:  # noqa: BLE001
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"I attempted to enter an invalid name: {e}"
                        f" I need to pay closer attention to the rules and try again."
                    ),
                ),
            )
            return self.raw_memory

        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=f"Successfully entered the name {name}.",
            ),
        )
        return self.raw_memory

    async def _get_desired_name(self, game_state: YellowLegacyGameState) -> str:
        """Get the desired name from the LLM."""
        prompt = GET_NAME_PROMPT.format(state=self.state_string_builder(game_state))
        response = await self.llm_service.get_llm_response_pydantic(
            prompt,
            schema=NameResponse,
            prompt_name="get_name",
        )
        self.raw_memory.append(RawMemoryPiece(iteration=self.iteration, content=response.thoughts))
        return response.name

    async def _enter_name(self, name: str) -> None:
        """Enter the name into the game."""
        for letter in name:
            game_state = self.emulator.get_game_state()
            argwhere_letter = np.argwhere(letter == LETTER_ARR)
            if len(argwhere_letter) != 1:
                raise ValueError(f"Invalid letter: {letter}")

            letter_loc: tuple[int, int] = tuple(argwhere_letter[0])
            cursor_loc = game_state.screen.cursor_index
            dir_buttons = self._get_dir_buttons(letter_loc, cursor_loc)

            await self.emulator.press_buttons(
                [*dir_buttons, Button.A],
                frames_between=GAME_TICKS_PER_SECOND // 2,
            )

        await self.emulator.press_buttons([Button.START])  # Accept the name.

    def _get_dir_buttons(self, letter_loc: tuple[int, int], cursor_loc: int) -> list[Button]:
        """
        Get the direction buttons to press to get to the letter.

        Row 1 starts at cursor_loc 5 for A, adds 2 for each letter, ending at 21 for I.
        Row 2 starts at 45 for J, adds 2 for each letter, ending at 61 for R.
        Row 3 starts at 85 for S, adds 2 for each letter, with 99 for Z, ending at 101 for space.

        :param letter_loc: The (row, col) location of the letter in the LETTER_ARR.
        :param cursor_loc: The index of the cursor on the screen.
        :return: The direction buttons to press.
        """
        cursor_row = cursor_loc // 40
        cursor_col = (cursor_loc % 40 - 5) // 2

        row_diff = letter_loc[0] - cursor_row
        col_diff = letter_loc[1] - cursor_col

        # If moving more than half the width, it's shorter to go the other way
        num_cols = 9
        if abs(col_diff) > num_cols // 2:
            col_diff = (col_diff + num_cols) % num_cols - num_cols

        buttons = []
        if row_diff > 0:
            buttons += [Button.DOWN] * row_diff
        elif row_diff < 0:
            buttons += [Button.UP] * -row_diff
        if col_diff > 0:
            buttons += [Button.RIGHT] * col_diff
        elif col_diff < 0:
            buttons += [Button.LEFT] * -col_diff
        return buttons
