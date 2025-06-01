import numpy as np

from common.constants import GAME_TICKS_PER_SECOND
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
from memory.raw_memory import RawMemory, RawMemoryPiece

LETTER_ARR = np.array(
    [
        ["A", "B", "C", "D", "E", "F", "G", "H", "I"],
        ["J", "K", "L", "M", "N", "O", "P", "Q", "R"],
        ["S", "T", "U", "V", "W", "X", "Y", "Z", " "],
    ],
)
BUTTON_DELAY_FRAMES = GAME_TICKS_PER_SECOND // 2


class AssignNameService:
    """A service that assigns a name to something in the game."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.emulator = emulator

    async def assign_name(self) -> RawMemory:
        """
        Assign a name to something in the game.

        :return: The raw memory, and the handler to use if subsequent handling is needed.
        """
        game_state = self.emulator.get_game_state()
        onscreen_text = game_state.get_onscreen_text()
        first_name_row = "A B C D E F G H I"
        if first_name_row not in onscreen_text:
            # Should never happen if we're in this handler, but just in case we need to bail.
            return self.raw_memory

        name = await self._get_desired_name()  # TODO: Handle invalid names.
        name = list(name.upper())

        for letter in name:
            argwhere_letter = np.argwhere(LETTER_ARR == letter)
            if len(argwhere_letter) != 1:
                raise ValueError(f"Invalid letter: {letter}")

            letter_loc: tuple[int, int] = tuple(argwhere_letter[0])
            cursor_loc = game_state.screen.cursor_index
            dir_buttons = self._get_dir_buttons(letter_loc, cursor_loc)

            await self.emulator.press_buttons(
                [*dir_buttons, Button.A],
                frames_between=BUTTON_DELAY_FRAMES,
            )
            game_state = self.emulator.get_game_state()

        await self.emulator.press_buttons([Button.START])  # Accept the name.

        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=f"Successfully entered the name {name}.",
            ),
        )
        return self.raw_memory

    async def _get_desired_name(self) -> str:
        """Get the desired name from the LLM."""
        return "TST NNE"

    def _get_dir_buttons(self, letter_loc: tuple[int, int], cursor_loc: int) -> list[Button]:
        """
        Get the direction buttons to press to get to the letter.

        Row 1 starts at cursor_loc 5 for A, adds 2 for each letter, ending at 21 for I.
        Row 2 starts at 45 for J, adds 2 for each letter, ending at 61 for R.
        Row 3 starts at 85 for S, adds 2 for each letter, with 99 for Z and 101 for space.

        :param letter_loc: The (row, col) location of the letter in the LETTER_ARR.
        :param cursor_loc: The index of the cursor on the screen.
        :return: The direction buttons to press.
        """
        cursor_row = cursor_loc // 40
        cursor_col = (cursor_loc % 40 - 5) // 2

        row_diff = letter_loc[0] - cursor_row
        col_diff = letter_loc[1] - cursor_col

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
