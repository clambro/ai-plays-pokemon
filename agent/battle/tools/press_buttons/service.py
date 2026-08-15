"""Deterministic button input for irregular battle screens."""

from typing import TYPE_CHECKING

from agent.utils import is_battle_handler_state

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agent.context import AgentContext
    from common.enums import Button
    from emulator.control_events import ControlBoundary


async def press_buttons(
    *,
    context: AgentContext,
    buttons: Sequence[Button],
) -> tuple[str, ControlBoundary | None]:
    """Press the selected buttons.

    Args:
        context: Battle dependencies.
        buttons: Buttons to press in order.

    Returns:
        Confirmation of the buttons pressed and the final ROM control boundary.
    """
    pressed_buttons: list[str] = []
    final_boundary = None
    for index, button in enumerate(buttons):
        control_result = await context.emulator.press_button(button)
        final_boundary = control_result.boundary
        pressed_buttons.append(button.value)

        if index < len(buttons) - 1:
            game_state = await context.emulator.get_game_state()
            if not is_battle_handler_state(game_state):
                break

    return f"Pressed the following buttons: {pressed_buttons}.", final_boundary
