"""Pydantic AI interface for recalling observed cross-map routes."""

from typing import TYPE_CHECKING

from pydantic_ai import Tool

from agent.overworld.tools.recall_route.schemas import RouteSearchState
from agent.overworld.tools.recall_route.service import recall_route as recall_route_service
from agent.overworld.tools.utils import OverworldToolResult, complete_overworld_action

if TYPE_CHECKING:
    from agent.context import AgentContext
    from agent.overworld.map_view import CurrentMapView
    from emulator.game_state import GameState


def build_recall_route_tool(
    context: AgentContext,
    map_view: CurrentMapView,
    game_state: GameState,
) -> Tool[AgentContext]:
    """Build the route-recall tool for the current overworld region."""

    async def recall_route(destination: str) -> OverworldToolResult:
        """Recall how to reach a map that you have previously visited.

        Use this when you remember a destination but not the sequence of maps,
        warps, ladders, or boundaries needed to return there. Pass the exact map
        name from your current observations or memory. The result contains one
        shortest known route using only transitions you have previously taken
        and terrain you have explored.

        This tool provides directions but does not move you. Follow the route
        one transition at a time with navigation and press_buttons. If no known
        route exists, continue exploring rather than inventing a connection.

        Args:
            destination: Name of a previously visited destination map.

        Returns:
            Fresh screenshot and remembered directions to the destination.
        """
        current_map = map_view.overworld_map
        result = await recall_route_service(
            destination=destination,
            search=RouteSearchState(
                map_id=current_map.id,
                coords=game_state.player.coords,
                reachable_coords=map_view.reachable_coords,
                hm_tiles=game_state.get_hm_tiles(),
                visited_map_ids=current_map.known_map_ids,
            ),
            rolling_memory=context.state.rolling_memory,
        )
        return await complete_overworld_action(context, result)

    return Tool(recall_route, require_parameter_descriptions=True)
