"""Tool registry for the Pydantic AI battle agent."""

from typing import TYPE_CHECKING

from pydantic_ai import FunctionToolset

from agent.subflows.battle_handler.tools.fight.interface import build_fight_tool
from agent.subflows.battle_handler.tools.press_buttons.interface import build_press_buttons_tool
from agent.subflows.battle_handler.tools.run.interface import build_run_tool
from agent.subflows.battle_handler.tools.switch_pokemon.interface import (
    build_switch_pokemon_tool,
)
from agent.subflows.battle_handler.tools.throw_ball.interface import build_throw_ball_tool
from common.enums import BattleType

if TYPE_CHECKING:
    from pydantic_ai import Tool

    from agent.context import AgentContext


def build_battle_toolset(
    context: AgentContext,
    battle_type: BattleType | None,
) -> FunctionToolset[AgentContext]:
    """Build the fixed toolset for the current battle type."""
    tools: list[Tool[AgentContext]] = []
    if battle_type in (BattleType.TRAINER, BattleType.WILD):
        tools.extend(
            (
                build_fight_tool(context),
                build_switch_pokemon_tool(context),
            ),
        )
    if battle_type == BattleType.WILD:
        tools.append(build_throw_ball_tool(context))
        tools.append(build_run_tool(context))
    tools.append(build_press_buttons_tool(context))
    return FunctionToolset(tools=tools)
