"""Deterministic button input for irregular battle screens."""

from typing import TYPE_CHECKING

from agent.utils import is_battle_handler_state

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agent.context import AgentContext
    from common.enums import Button


async def press_buttons(
    *,
    context: AgentContext,
    buttons: Sequence[Button],
) -> str:
    """Press the selected buttons.

    Args:
        context: Battle dependencies.
        buttons: Buttons to press in order.

    Returns:
        Confirmation of the buttons pressed.
    """
    pressed_buttons: list[str] = []
    for index, button in enumerate(buttons):
        await context.emulator.press_button(
            button,
            wait_for_animation=index < len(buttons) - 1,
        )
        pressed_buttons.append(button.value)

        if index < len(buttons) - 1:
            game_state = await context.emulator.get_game_state()
            if not is_battle_handler_state(game_state):
                break

    return f"Pressed the following buttons: {pressed_buttons}."
