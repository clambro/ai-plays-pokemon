"""Tool registry for the Pydantic AI battle agent."""

from typing import TYPE_CHECKING

from pydantic_ai import FunctionToolset

from agent.battle.tools.fight.interface import build_fight_tool
from agent.battle.tools.press_buttons.interface import build_press_buttons_tool
from agent.battle.tools.run.interface import build_run_tool
from agent.battle.tools.switch_pokemon.interface import (
    build_switch_pokemon_tool,
)
from agent.battle.tools.throw_ball.interface import build_throw_ball_tool
from common.enums import BattleType

if TYPE_CHECKING:
    from pydantic_ai import Tool

    from agent.context import AgentContext


def build_battle_toolset(
    context: AgentContext,
    battle_type: BattleType | None,
    *,
    enemy_family_caught: bool,
) -> FunctionToolset[AgentContext]:
    """Build the fixed toolset for the current battle state."""
    tools: list[Tool[AgentContext]] = []
    if battle_type in (BattleType.TRAINER, BattleType.WILD):
        tools.extend(
            (
                build_fight_tool(context),
                build_switch_pokemon_tool(context),
            ),
        )
    if battle_type == BattleType.WILD:
        if not enemy_family_caught:
            tools.append(build_throw_ball_tool(context))
        tools.append(build_run_tool(context))
    tools.append(build_press_buttons_tool(context))
    return FunctionToolset(tools=tools)
