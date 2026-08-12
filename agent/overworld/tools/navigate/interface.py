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

        The navigation tool allows you to navigate to any revealed, accessible
        tile on the current map using an A* search algorithm. It is useful for:

        - Moving the player around the current map. This should be your primary
          mode of movement, especially if you are trying to move more than a
          single tile at a time.
        - Moving to a specific tile type (e.g. moving into tall grass or water
          to find wild Pokemon. You need access to Surf to move into water).
        - Revealing unexplored territory on the current map.
        - Navigating directly to warp tiles.
        - Navigating to the boundaries of the current map.

        The navigation tool can navigate beyond the current screen, but it
        plans paths only within the current map and cannot target coordinates
        on another map. For a direct outdoor connection, navigate to the edge
        and cross it in the next iteration. The tool can navigate directly onto
        an accessible warp tile; if that step changes maps, navigation ends
        after the transition.

        The navigation tool cannot be used to interact with entities, but it
        can be used to move to the tile next to them so that you can interact
        with them via the button tool on the next iteration.

        The navigation tool intentionally tries to avoid random encounters with
        wild Pokemon for smoother navigation, and is thus not an efficient way
        to find wild Pokemon.

        Do not attempt to navigate to the tile that you are currently standing
        on. This does nothing.

        Navigating directly to warp tiles that are marked in your overworld map
        as not yet visited is another effective way to explore new areas. Doing
        so will take you to a new map, usually a building, a cave, or a new
        floor of a building or cave.

        The row and column must be one of the ``accessible_coords`` provided in
        the prompt. Do not invent coordinates.

        When choosing a destination:

        - Navigate directly to a specific warp, boundary, or location when it
          is accessible.
        - To interact with a sprite, sign, or object, navigate to an accessible
          adjacent coordinate.
        - When seeking a specific tile type, select an accessible coordinate of
          that type.
        - When seeking wild Pokemon, select suitable grass, cave, or water at
          least five tiles away so the route crosses more encounter-capable
          tiles.
        - Replace an inaccessible requested destination with the accessible
          coordinate that best satisfies the same intent.

        Args:
            row: Map row from the provided accessible coordinates.
            col: Map column from the provided accessible coordinates.

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
