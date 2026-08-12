"""Pydantic AI interface for overworld navigation."""

from typing import TYPE_CHECKING

from pydantic_ai import Tool

from agent.overworld.tools.navigate.service import NavigationService
from agent.overworld.tools.utils import (
    OverworldToolResult,
    complete_overworld_action,
)
from common.schemas import Coords

if TYPE_CHECKING:
    from agent.context import AgentContext
    from overworld_map.schemas import OverworldMap


def build_navigation_tool(
    context: AgentContext,
    current_map: OverworldMap,
) -> Tool[AgentContext]:
    """Build the navigation tool bound to the current overworld context."""

    async def navigation(row: int, col: int) -> OverworldToolResult:
        """Navigate to a revealed, accessible tile on the current map.

        This should be your primary mode of ordinary movement, especially when
        moving more than one tile. It uses an A* search to reach accessible
        coordinates beyond the current screen, including exploration
        candidates, specific terrain, known warp tiles, and map boundaries.

        Paths are planned only within the current map and cannot target
        coordinates on another map. For a direct outdoor connection, navigate
        to the edge and cross it in the next iteration. The tool can navigate
        directly onto an accessible warp tile; if that step changes maps,
        navigation ends after the transition.

        This tool cannot interact with entities. To interact with a sprite,
        sign, or object, navigate to an accessible adjacent coordinate.

        Navigation intentionally avoids random encounters where possible. When
        deliberately seeking wild Pokemon, choose suitable grass, cave, or
        water at least five tiles away so that the route crosses more
        encounter-capable tiles.

        Do not attempt to navigate to the tile that you are currently standing
        on. This does nothing.

        Choose a revealed coordinate from the current map. The tool will reject
        coordinates that cannot be reached from the current position.

        Args:
            row: Target row on the current map.
            col: Target column on the current map.

        Returns:
            Fresh screenshot and the actual navigation result.
        """
        state = context.state
        target = Coords(row=row, col=col)
        service = NavigationService(
            iteration=state.iteration,
            emulator=context.emulator,
            current_map=current_map,
            rolling_memory=state.rolling_memory,
        )
        result = await service.navigate(target)
        return await complete_overworld_action(context, result)

    return Tool(navigation, require_parameter_descriptions=True)
