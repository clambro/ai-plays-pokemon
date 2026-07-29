"""Deterministic button input for actionable text screens."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agent.subflows.text_handler.context import TextContext
    from common.enums import Button


async def press_buttons(*, context: TextContext, buttons: Sequence[Button]) -> str:
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
        await context.emulator.press_button(button)
        pressed_buttons.append(button.value)

        game_state = await context.emulator.get_game_state()
        if not game_state.is_text_on_screen() or game_state.battle.is_in_battle:
            break
        if game_state.screen.tiles == previous_state.screen.tiles:
            result = f"The screen did not change after pressing {button.value}."
            break

    action = f"Pressed the following buttons: {pressed_buttons}."
    return f"{action} {result}".strip()
