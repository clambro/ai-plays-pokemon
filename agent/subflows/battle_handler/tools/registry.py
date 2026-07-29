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
from agent.subflows.battle_handler.utils import is_fight_menu_open
from common.enums import BattleType, PokeballItem

if TYPE_CHECKING:
    from pydantic_ai import Tool

    from agent.subflows.battle_handler.context import BattleContext


def build_battle_toolset(context: BattleContext) -> FunctionToolset[BattleContext]:
    """Build the tools available for the prepared battle state."""
    game_state = context.game_state
    battle = game_state.battle
    if (
        not battle.is_in_battle
        or battle.battle_type not in (BattleType.TRAINER, BattleType.WILD)
        or not is_fight_menu_open(game_state)
    ):
        return FunctionToolset(tools=[build_press_buttons_tool(context)])

    tools: list[Tool[BattleContext]] = []
    player_pokemon = battle.player_pokemon
    if player_pokemon is not None:
        tools.append(build_fight_tool(context))
        if any(
            (pokemon.name, pokemon.species) != (player_pokemon.name, player_pokemon.species)
            and pokemon.hp > 0
            for pokemon in game_state.party
        ):
            tools.append(build_switch_pokemon_tool(context))

    if battle.battle_type == BattleType.WILD:
        inventory_names = {item.name for item in game_state.inventory.items}
        if any(ball.value in inventory_names for ball in PokeballItem):
            tools.append(build_throw_ball_tool(context))
        tools.append(build_run_tool(context))

    if not tools:
        tools.append(build_press_buttons_tool(context))
    return FunctionToolset(tools=tools)
