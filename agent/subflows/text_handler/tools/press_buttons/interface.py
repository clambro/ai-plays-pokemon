"""Pydantic AI interface for text-screen button input."""

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field
from pydantic_ai import Tool

from agent.subflows.text_handler.tools.press_buttons.service import (
    press_buttons as press_buttons_service,
)
from common.enums import Button

if TYPE_CHECKING:
    from agent.subflows.text_handler.context import TextContext

type TextButton = Literal[
    Button.A,
    Button.B,
    Button.START,
    Button.UP,
    Button.DOWN,
    Button.LEFT,
    Button.RIGHT,
]


def build_press_buttons_tool(context: TextContext) -> Tool[TextContext]:
    """Build the button-input tool bound to the current text context."""

    async def press_buttons(
        buttons: Annotated[list[TextButton], Field(min_length=1)],
    ) -> str:
        """Press buttons to respond to the current text screen.

        The available buttons are:

        - ``a`` selects the highlighted option or progresses on-screen text.
        - ``b`` returns to the previous screen or declines a question.
        - ``start`` sorts the bag when the bag screen is open.
        - ``up`` moves the cursor up one row.
        - ``down`` moves the cursor down one row.
        - ``left`` moves the cursor left one column.
        - ``right`` moves the cursor right one column.

        Prefer one button at a time. Use a short sequence only when navigating
        to a clearly identified menu choice. If you are stuck in an unfamiliar
        nested menu, pressing ``b`` several times will usually back out of it.

        Args:
            buttons: Buttons to press in order.

        Returns:
            The result of the attempted button sequence.
        """
        return await press_buttons_service(
            context=context,
            buttons=buttons,
        )

    return Tool(press_buttons, require_parameter_descriptions=True)
