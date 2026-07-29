"""Deterministic name entry for the text agent."""

from typing import TYPE_CHECKING

import numpy as np

from agent.subflows.text_handler.tools.errors import TextActionUnavailableError
from common.enums import Button

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState

_LETTER_GRID = np.array(
    [
        ["A", "B", "C", "D", "E", "F", "G", "H", "I"],
        ["J", "K", "L", "M", "N", "O", "P", "Q", "R"],
        ["S", "T", "U", "V", "W", "X", "Y", "Z", " "],
    ],
)


async def assign_name(
    *,
    emulator: YellowLegacyEmulator,
    name: str,
) -> str:
    """Enter a name through the game's naming screen.

    Args:
        emulator: Running emulator used to inspect and operate the naming screen.
        name: Name to enter.

    Returns:
        Confirmation of the entered name.

    Raises:
        TextActionUnavailableError: The naming screen is not open or the name is unavailable.
    """
    game_state = await emulator.get_game_state()
    if not game_state.is_naming_screen():
        raise TextActionUnavailableError("The naming screen is not open.")

    _validate_name_uniqueness(name, game_state)
    await _enter_name(emulator, name)
    return f"Entered the name {name}."


def _validate_name_uniqueness(
    name: str,
    game_state: YellowLegacyGameState,
) -> None:
    """Reject a name already used by the player or one of their Pokemon."""
    existing_names = [
        game_state.player.name,
        *[pokemon.name for pokemon in game_state.party],
        *[pokemon.name for pokemon in game_state.pc_pokemon],
    ]
    if name in existing_names:
        raise TextActionUnavailableError(f"The name {name} is already in use.")


async def _enter_name(
    emulator: YellowLegacyEmulator,
    name: str,
) -> None:
    """Navigate the naming grid and confirm the supplied name."""
    for letter in name:
        game_state = await emulator.get_game_state()
        matching_positions = np.argwhere(letter == _LETTER_GRID)
        if len(matching_positions) != 1:
            raise TextActionUnavailableError(f"The character {letter!r} cannot be entered.")

        letter_location: tuple[int, int] = tuple(matching_positions[0])
        cursor_location = game_state.screen.cursor_index
        for button in _get_dir_buttons(letter_location, cursor_location):
            await emulator.press_button(button)
        await emulator.press_button(Button.A)

    await emulator.press_button(Button.START)


def _get_dir_buttons(
    letter_location: tuple[int, int],
    cursor_location: int,
) -> list[Button]:
    """Get the direction buttons needed to reach a letter.

    Row 1 starts at cursor index 5 for A, adds 2 for each letter, and ends at
    21 for I. Row 2 starts at 45 for J and ends at 61 for R. Row 3 starts at
    85 for S, reaches 99 for Z, and ends at 101 for a space.

    Args:
        letter_location: Row and column of the letter in the naming grid.
        cursor_location: Current cursor index on the naming screen.

    Returns:
        Directional button presses that move the cursor to the letter.
    """
    cursor_row = cursor_location // 40
    cursor_column = (cursor_location % 40 - 5) // 2

    row_difference = letter_location[0] - cursor_row
    column_difference = letter_location[1] - cursor_column

    num_columns = 9
    if column_difference > num_columns // 2:
        column_difference -= num_columns
    elif column_difference < -num_columns // 2:
        column_difference += num_columns

    buttons = []
    if row_difference > 0:
        buttons += [Button.DOWN] * row_difference
    elif row_difference < 0:
        buttons += [Button.UP] * -row_difference
    if column_difference > 0:
        buttons += [Button.RIGHT] * column_difference
    elif column_difference < 0:
        buttons += [Button.LEFT] * -column_difference
    return buttons
