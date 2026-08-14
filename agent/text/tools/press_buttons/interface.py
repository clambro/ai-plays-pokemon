"""Pydantic AI interface for text-screen button input."""

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field
from pydantic_ai import Tool

from agent.text.tools.errors import TextActionUnavailableError
from agent.text.tools.press_buttons.service import (
    press_buttons as press_buttons_service,
)
from agent.text.utils import TextToolResult, complete_text_action
from common.enums import Button

if TYPE_CHECKING:
    from agent.context import AgentContext

type TextButton = Literal[
    Button.A,
    Button.B,
    Button.START,
    Button.UP,
    Button.DOWN,
    Button.LEFT,
    Button.RIGHT,
]


def build_press_buttons_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the button-input tool bound to the current text context."""

    async def press_buttons(
        buttons: Annotated[list[TextButton], Field(min_length=1)],
    ) -> TextToolResult:
        """Press buttons to respond to the current interactive screen.

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
            Fresh text context after pressing the buttons.
        """
        try:
            result = await press_buttons_service(
                context=context,
                buttons=buttons,
            )
        except TextActionUnavailableError as error:
            return await complete_text_action(context, str(error))
        return await complete_text_action(context, result)

    return Tool(press_buttons, require_parameter_descriptions=True)
