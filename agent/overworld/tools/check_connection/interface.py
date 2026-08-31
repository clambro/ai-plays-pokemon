"""Pydantic AI interface for checking remembered map connectivity."""

from typing import TYPE_CHECKING

from pydantic_ai import Tool

from agent.overworld.tools.check_connection.service import (
    check_connection as check_connection_service,
)
from common.schemas import Coords  # noqa: TC001 - Pydantic AI needs the runtime model.

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState


def build_check_connection_tool(
    context: AgentContext,
    game_state: GameState,
) -> Tool[AgentContext]:
    """Build the connection-checking tool for the current overworld context."""

    async def check_connection(
        map_name: str,
        coordinates: Coords,
    ) -> str:
        """Check where a previously discovered map connection leads.

        Use this to reconstruct a route through a previously visited multi-map
        area without moving. Pass the named map and one coordinate from a
        connection shown on the current map or in a previous check result. The
        result follows the complete connection, lists other discovered
        connections reachable from its destination, and reports whether that
        region still has unexplored terrain. Check one of the returned
        connections to continue reconstructing the route.

        This tool does not move, choose a route, reveal unvisited maps, or infer
        connections that have not been discovered.

        Args:
            map_name: Uppercase map name shown with the connection.
            coordinates: Any listed coordinate belonging to the connection.

        Returns:
            Known connections and exploration status on the destination map component.
        """
        result = await check_connection_service(
            map_name=map_name,
            coordinates=coordinates,
            hm_tiles=game_state.get_hm_tiles(),
        )
        context.state.rolling_memory.add_memory(result)
        return result

    return Tool(check_connection, require_parameter_descriptions=True)
