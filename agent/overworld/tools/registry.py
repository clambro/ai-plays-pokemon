"""Tool registry for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from pydantic_ai import FunctionToolset

from agent.overworld.tools.navigate.interface import build_navigation_tool
from agent.overworld.tools.press_buttons.interface import (
    build_press_buttons_tool,
)
from agent.overworld.tools.recall_route.interface import build_recall_route_tool
from agent.overworld.tools.set_goal.interface import build_set_goal_tool
from agent.overworld.tools.sokoban_solver.interface import (
    build_sokoban_solver_tool,
)
from agent.overworld.tools.swap_first_pokemon.interface import (
    build_swap_first_pokemon_tool,
)
from agent.overworld.tools.use_item.interface import build_use_item_tool
from common.enums import AsciiTile, SpriteLabel

if TYPE_CHECKING:
    from pydantic_ai import Tool

    from agent.context import AgentContext
    from agent.overworld.map_view import CurrentMapView
    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap

_FORCED_GOAL_UPDATE_INTERVAL = 300


def build_overworld_toolset(
    context: AgentContext,
    current_map: OverworldMap,
    map_view: CurrentMapView,
    game_state: GameState,
) -> FunctionToolset[AgentContext]:
    """Build the fixed toolset available for the current overworld state."""
    latest_goal_update = max(
        (goal.updated_at_iteration for goal in context.state.goals.goals),
        default=0,
    )
    if context.state.iteration - latest_goal_update >= _FORCED_GOAL_UPDATE_INTERVAL:
        return FunctionToolset(tools=[build_set_goal_tool(context, end_turn_on_success=True)])

    tools: list[Tool[AgentContext]] = [
        build_press_buttons_tool(context),
        build_recall_route_tool(context, map_view, game_state),
        build_set_goal_tool(context),
    ]
    if not game_state.player.is_biking:
        tools.append(build_navigation_tool(context, current_map))
    if game_state.player.has_pokedex:
        if len(game_state.party) > 1:
            tools.append(build_swap_first_pokemon_tool(context))
        if game_state.inventory.items:
            tools.append(build_use_item_tool(context))
    if _is_sokoban_available(map_view, game_state):
        tools.append(build_sokoban_solver_tool(context, current_map))
    return FunctionToolset(tools=tools)


def _is_sokoban_available(
    map_view: CurrentMapView,
    game_state: GameState,
) -> bool:
    """Check whether the current map contains a usable Sokoban puzzle."""
    if not game_state.can_use_strength:
        return False

    current_map = map_view.overworld_map
    has_goal = any(
        current_map.terrain[coords.row][coords.col]
        in (AsciiTile.BOULDER_HOLE, AsciiTile.PRESSURE_PLATE)
        for coords in map_view.visible_coords
    )
    has_boulder = any(
        sprite.label == SpriteLabel.BOULDER
        and sprite.is_rendered
        and sprite.coords in map_view.visible_coords
        for entity_id in current_map.known_sprite_ids
        if (sprite := game_state.sprites.get(entity_id)) is not None
    )
    return has_goal and has_boulder
