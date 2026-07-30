"""Tool registry for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from pydantic_ai import FunctionToolset

from agent.subflows.overworld_handler.tools.navigate.interface import build_navigation_tool
from agent.subflows.overworld_handler.tools.press_buttons.interface import (
    build_press_buttons_tool,
)
from agent.subflows.overworld_handler.tools.sokoban_solver.interface import (
    build_sokoban_solver_tool,
)
from agent.subflows.overworld_handler.tools.swap_first_pokemon.interface import (
    build_swap_first_pokemon_tool,
)
from agent.subflows.overworld_handler.tools.update_signs.interface import (
    build_update_signs_tool,
)
from agent.subflows.overworld_handler.tools.update_sprites.interface import (
    build_update_sprites_tool,
)
from agent.subflows.overworld_handler.tools.use_item.interface import build_use_item_tool
from common.enums import AsciiTile, SpriteLabel

if TYPE_CHECKING:
    from pydantic_ai import Tool

    from agent.subflows.overworld_handler.context import OverworldContext
    from emulator.game_state import YellowLegacyGameState


def build_overworld_toolset(
    context: OverworldContext,
    game_state: YellowLegacyGameState,
) -> FunctionToolset[OverworldContext]:
    """Build the fixed toolset available for the current overworld state."""
    tools: list[Tool[OverworldContext]] = [build_press_buttons_tool(context)]
    if not game_state.player.is_biking:
        tools.append(build_navigation_tool(context))
    if len(game_state.party) > 1:
        tools.append(build_swap_first_pokemon_tool(context))
    if game_state.inventory.items:
        tools.append(build_use_item_tool(context))
    if _is_sokoban_available(context, game_state):
        tools.append(build_sokoban_solver_tool(context))
    current_map = context.state.current_map
    if current_map is not None:
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
            tools.append(build_update_sprites_tool(context, nearby_sprites))
        if nearby_signs:
            tools.append(build_update_signs_tool(context, nearby_signs))
    return FunctionToolset(tools=tools)


def _is_sokoban_available(
    context: OverworldContext,
    game_state: YellowLegacyGameState,
) -> bool:
    """Check whether the current map contains a usable Sokoban puzzle."""
    current_map = context.state.current_map
    if current_map is None or not game_state.can_use_strength:
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
