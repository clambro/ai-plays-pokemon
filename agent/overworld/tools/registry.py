"""Tool registry for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from pydantic_ai import FunctionToolset

from agent.overworld.tools.create_goal.interface import (
    build_create_goal_tool,
)
from agent.overworld.tools.create_long_term_memory.interface import (
    build_create_long_term_memory_tool,
)
from agent.overworld.tools.delete_goal.interface import (
    build_delete_goal_tool,
)
from agent.overworld.tools.navigate.interface import build_navigation_tool
from agent.overworld.tools.press_buttons.interface import (
    build_press_buttons_tool,
)
from agent.overworld.tools.retrieve_long_term_memory.interface import (
    build_retrieve_long_term_memory_tool,
)
from agent.overworld.tools.sokoban_solver.interface import (
    build_sokoban_solver_tool,
)
from agent.overworld.tools.swap_first_pokemon.interface import (
    build_swap_first_pokemon_tool,
)
from agent.overworld.tools.update_goal.interface import (
    build_update_goal_tool,
)
from agent.overworld.tools.update_long_term_memory.interface import (
    build_update_long_term_memory_tool,
)
from agent.overworld.tools.update_signs.interface import (
    build_update_signs_tool,
)
from agent.overworld.tools.update_sprites.interface import (
    build_update_sprites_tool,
)
from agent.overworld.tools.use_item.interface import build_use_item_tool
from common.enums import AsciiTile, SpriteLabel

if TYPE_CHECKING:
    from pydantic_ai import Tool

    from agent.context import AgentContext
    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap


def build_overworld_toolset(
    context: AgentContext,
    current_map: OverworldMap,
    available_long_term_memory_titles: list[str],
    game_state: GameState,
) -> FunctionToolset[AgentContext]:
    """Build the fixed toolset available for the current overworld state."""
    tools: list[Tool[AgentContext]] = [
        build_press_buttons_tool(context),
        build_create_goal_tool(context),
        build_update_goal_tool(context),
        build_delete_goal_tool(context),
        build_create_long_term_memory_tool(context, available_long_term_memory_titles),
        build_update_long_term_memory_tool(context),
    ]
    if available_long_term_memory_titles:
        tools.append(
            build_retrieve_long_term_memory_tool(
                context,
                available_long_term_memory_titles,
            ),
        )
    if not game_state.player.is_biking:
        tools.append(build_navigation_tool(context, current_map))
    if game_state.player.has_pokedex:
        if len(game_state.party) > 1:
            tools.append(build_swap_first_pokemon_tool(context))
        if game_state.inventory.items:
            tools.append(build_use_item_tool(context))
    if _is_sokoban_available(current_map, game_state):
        tools.append(build_sokoban_solver_tool(context, current_map))
    max_distance = 2
    nearby_sprites = [
        sprite
        for sprite in current_map.known_sprites.values()
        if (sprite.coords - game_state.player.coords).length <= max_distance
    ]
    nearby_signs = [
        sign
        for sign in current_map.known_signs.values()
        if (sign.coords - game_state.player.coords).length <= max_distance
    ]
    if nearby_sprites:
        tools.append(build_update_sprites_tool(context, current_map, nearby_sprites))
    if nearby_signs:
        tools.append(build_update_signs_tool(context, current_map, nearby_signs))
    return FunctionToolset(tools=tools)


def _is_sokoban_available(
    current_map: OverworldMap,
    game_state: GameState,
) -> bool:
    """Check whether the current map contains a usable Sokoban puzzle."""
    if not game_state.can_use_strength:
        return False

    has_goal = any(
        tile in (AsciiTile.BOULDER_HOLE, AsciiTile.PRESSURE_PLATE)
        for row in current_map.ascii_tiles
        for tile in row
    )
    has_boulder = any(
        sprite.label == SpriteLabel.BOULDER and sprite.is_rendered
        for sprite in current_map.known_sprites.values()
    )
    return has_goal and has_boulder
