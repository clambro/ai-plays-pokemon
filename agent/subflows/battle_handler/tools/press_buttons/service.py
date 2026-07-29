"""Deterministic button input for irregular battle screens."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agent.subflows.battle_handler.context import BattleContext
    from common.enums import Button


async def press_buttons(
    *,
    context: BattleContext,
    reason: str,
    buttons: Sequence[Button],
) -> str:
    """Press the selected buttons and record the action in rolling memory.

    Args:
        context: Battle dependencies and working memory.
        reason: Brief explanation of the selected input.
        buttons: Buttons to press in order.

    Returns:
        Confirmation of the buttons pressed.
    """
    button_names = [button.value for button in buttons]
    context.rolling_memory.add_memory(
        content=f"{reason} Pressed the following buttons: {button_names}.",
    )
    for index, button in enumerate(buttons):
        await context.emulator.press_button(
            button,
            wait_for_animation=index < len(buttons) - 1,
        )
    return f"Pressed the following buttons: {button_names}."
