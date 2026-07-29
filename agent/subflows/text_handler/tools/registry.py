"""Tool registry for the Pydantic AI text agent."""

from typing import TYPE_CHECKING

from pydantic_ai import FunctionToolset

from agent.subflows.text_handler.tools.assign_name.interface import (
    build_assign_name_tool,
)
from agent.subflows.text_handler.tools.press_buttons.interface import (
    build_press_buttons_tool,
)

if TYPE_CHECKING:
    from agent.subflows.text_handler.context import TextContext


def build_text_toolset(context: TextContext) -> FunctionToolset[TextContext]:
    """Build the text agent's fixed toolset."""
    return FunctionToolset(
        tools=[
            build_press_buttons_tool(context),
            build_assign_name_tool(context),
        ],
    )
