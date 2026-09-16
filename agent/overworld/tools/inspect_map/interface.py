"""Pydantic AI interface for inspecting remembered map arrivals."""

from typing import TYPE_CHECKING

from pydantic_ai import Tool

from agent.overworld.formatting import format_map_inspection
from agent.overworld.tools.inspect_map import service

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState


def build_inspect_map_tool(
    context: AgentContext,
    game_state: GameState,
) -> Tool[AgentContext]:
    """Build the map-inspection tool for the current overworld context."""

    async def inspect_map(map_name: str) -> str:
        """Inspect every discovered entrance or arrival on a previously visited map.

        For each arrival coordinate, the result lists the connections reachable
        from there and whether exploration candidates remain. Different arrivals
        on the same map may reach different places, including one-way routes.
        Each arrival's results reflect reachability through currently revealed
        terrain, using your available traversal abilities.
        The result also identifies entrances with no known way to reach them.
        Match a connection's destination coordinates to its arrival entry when
        inspecting the next map. Inspect the destination maps in turn to continue
        reconstructing connectivity without moving.

        If you are unsure how to proceed, this tool can help you iteratively inspect
        maps along known reachable connections to look for a route forward or
        remaining exploration candidates.

        This tool does not move, choose a route, reveal unvisited maps, or infer
        connections that have not been discovered. It can be a useful way to decide
        where to go next before having to physically go there.

        Args:
            map_name: Uppercase name of a previously visited map.

        Returns:
            Known arrivals, their reachable connections, and exploration status.
        """
        inspection = await service.inspect_map(
            map_name=map_name,
            hm_tiles=game_state.get_hm_tiles(),
        )
        result = format_map_inspection(inspection, map_name=map_name)
        context.state.rolling_memory.add_memory(result)
        return result

    return Tool(inspect_map, require_parameter_descriptions=True)
