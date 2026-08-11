"""Deterministic button input for actionable text screens."""

from typing import TYPE_CHECKING

from agent.text.tools.errors import TextActionUnavailableError
from agent.utils import is_text_handler_state

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agent.context import AgentContext
    from common.enums import Button


async def press_buttons(*, context: AgentContext, buttons: Sequence[Button]) -> str:
    """Press the selected buttons until the text state changes or an action fails.

    Args:
        context: Text-agent dependencies.
        buttons: Buttons to press in order.

    Returns:
        The result of the attempted button sequence.
    """
    pressed_buttons: list[str] = []
    result = ""
    for button in buttons:
        previous_state = await context.emulator.get_game_state()
        if not is_text_handler_state(previous_state):
            raise TextActionUnavailableError("The text interaction is no longer active.")

        await context.emulator.press_button(button)
        pressed_buttons.append(button.value)

        game_state = await context.emulator.get_game_state()
        if not is_text_handler_state(game_state):
            break
        if game_state.screen.tiles == previous_state.screen.tiles:
            result = f"The screen did not change after pressing {button.value}."
            break

    action = f"Pressed the following buttons: {pressed_buttons}."
    return f"{action} {result}".strip()
