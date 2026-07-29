"""Tool registry for the Pydantic AI battle agent."""

from pydantic_ai import FunctionToolset

from agent.subflows.battle_handler.context import BattleContext
from agent.subflows.battle_handler.tools.press_buttons.interface import press_buttons

BATTLE_TOOLSET = FunctionToolset[BattleContext](
    tools=[press_buttons],
    require_parameter_descriptions=True,
)
