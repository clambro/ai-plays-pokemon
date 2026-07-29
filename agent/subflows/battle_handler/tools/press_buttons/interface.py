"""Pydantic AI interface for battle button input."""

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field
from pydantic_ai import Tool

from agent.subflows.battle_handler.tools.press_buttons.service import (
    press_buttons as press_buttons_service,
)
from common.enums import Button

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext

type BattleButton = Literal[
    Button.A,
    Button.B,
    Button.UP,
    Button.DOWN,
    Button.LEFT,
    Button.RIGHT,
]


def build_press_buttons_tool(context: BattleContext) -> Tool[BattleContext]:
    """Build the button-input tool bound to the current battle context."""

    async def press_buttons(
        reason: Annotated[str, Field(min_length=1)],
        buttons: Annotated[list[BattleButton], Field(min_length=1)],
    ) -> str:
        """Press buttons to navigate an irregular battle screen.

        The available buttons are:

        - ``a`` selects the highlighted option or progresses on-screen text.
        - ``b`` returns to the previous screen or declines a question.
        - ``up`` moves the cursor up one row.
        - ``down`` moves the cursor down one row.
        - ``left`` moves the cursor left one column.
        - ``right`` moves the cursor right one column.

        Prefer one button at a time. Use a short sequence only when navigating
        to a clearly identified menu choice.

        Args:
            reason: Brief first-person explanation of the current screen and selected input.
            buttons: Buttons to press in order.

        Returns:
            Confirmation of the buttons pressed.
        """
        return await press_buttons_service(
            context=context,
            reason=reason,
            buttons=buttons,
        )

    return Tool(press_buttons, require_parameter_descriptions=True)
