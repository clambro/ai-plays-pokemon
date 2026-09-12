"""Deterministic button input for actionable text screens."""

from typing import TYPE_CHECKING

from agent.text.tools.errors import TextActionUnavailableError
from agent.utils import is_text_handler_state

if TYPE_CHECKING:
    from collections.abc import Sequence

    from common.enums import Button
    from emulator.emulator import Emulator


async def press_buttons(*, emulator: Emulator, buttons: Sequence[Button]) -> str:
    """Press the selected buttons until the text state changes or an action fails.

    Args:
        emulator: Emulator receiving the inputs.
        buttons: Buttons to press in order.

    Returns:
        The result of the attempted button sequence.
    """
    pressed_buttons: list[str] = []
    result = ""
    for button in buttons:
        (
            previous_state,
            previous_boundary,
        ) = await emulator.get_game_state_with_control_boundary()
        if not is_text_handler_state(previous_state, previous_boundary):
            raise TextActionUnavailableError("The interactive screen is no longer active.")

        control_result = await emulator.press_button(button)
        pressed_buttons.append(button.value)

        game_state = await emulator.get_game_state()
        if not is_text_handler_state(game_state, control_result.boundary):
            break
        if game_state.screen.tiles == previous_state.screen.tiles:
            result = f"The screen did not change after pressing {button.value}."
            break

    action = f"Pressed the following buttons: {pressed_buttons}."
    return f"{action} {result}".strip()
