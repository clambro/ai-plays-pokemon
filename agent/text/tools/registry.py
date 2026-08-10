"""Tool registry for the Pydantic AI text agent."""

from typing import TYPE_CHECKING

from pydantic_ai import FunctionToolset

from agent.text.tools.assign_name.interface import (
    build_assign_name_tool,
)
from agent.text.tools.press_buttons.interface import (
    build_press_buttons_tool,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_text_toolset(context: AgentContext) -> FunctionToolset[AgentContext]:
    """Build the text agent's fixed toolset."""
    return FunctionToolset(
        tools=[
            build_press_buttons_tool(context),
            build_assign_name_tool(context),
        ],
    )
