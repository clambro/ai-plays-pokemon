"""Pydantic AI interface for flying to a visited town."""

from typing import TYPE_CHECKING

from pydantic_ai import Tool

from agent.overworld.tools.fly.service import fly as fly_service
from agent.overworld.tools.utils import OverworldToolResult, complete_overworld_action
from common.enums import MapId  # noqa: TC001

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_fly_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the Fly tool when the party and current map permit it."""

    async def fly(destination: MapId) -> OverworldToolResult:
        """Fly to a previously visited town or city.

        Args:
            destination: Map ID of the town or city to fly to.

        Returns:
            Fresh screenshot and the actual result of the flight.
        """
        result = await fly_service(
            rolling_memory=context.state.rolling_memory,
            emulator=context.emulator,
            destination=destination,
        )
        return await complete_overworld_action(context, result)

    return Tool(fly, require_parameter_descriptions=True)
