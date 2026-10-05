"""Tool registry for the Pydantic AI text agent."""

from typing import TYPE_CHECKING

from pydantic_ai import FunctionToolset

from agent.text.tools.assign_name.interface import (
    build_assign_name_tool,
)
from agent.text.tools.press_buttons.interface import (
    build_press_buttons_tool,
)
from agent.text.tools.select_pc_pokemon.interface import build_select_pc_pokemon_tool

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_text_toolset(
    context: AgentContext,
    initial_screen_text: str,
) -> FunctionToolset[AgentContext]:
    """Build a fixed toolset based on the text screen at entry."""
    tools = [build_press_buttons_tool(context), build_assign_name_tool(context)]
    if any(label in initial_screen_text for label in ("BILL's PC", "SOMEONE's PC", "BOX No.")):
        tools.append(build_select_pc_pokemon_tool(context))
    return FunctionToolset(tools=tools)
