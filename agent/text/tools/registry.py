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
from agent.text.tools.use_item.interface import build_use_item_tool

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.parsers.screen import Screen


def build_text_toolset(
    context: AgentContext,
    initial_screen: Screen,
) -> FunctionToolset[AgentContext]:
    """Build a fixed toolset based on the text screen at entry."""
    tools = [build_press_buttons_tool(context), build_assign_name_tool(context)]
    if initial_screen.pokemon_list_source is not None:
        tools.append(build_select_pc_pokemon_tool(context))
    if initial_screen.is_bag_menu:
        tools.append(build_use_item_tool(context))
    return FunctionToolset(tools=tools)
