"""Temporary Junjo adapter for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger
from pydantic_ai import AgentRunError

from agent.state import AgentStore
from agent.subflows.overworld_handler.agent import run_overworld

if TYPE_CHECKING:
    from agent.context import AgentContext


class OverworldAgentNode(Node[AgentStore]):
    """Run one Pydantic AI overworld conversation."""

    def __init__(self, context: AgentContext) -> None:
        """Initialize the overworld-agent node."""
        self.context = context
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """Run the overworld agent through the shared context."""
        del store
        logger.info("Running the overworld agent...")

        try:
            await run_overworld(self.context)
        except AgentRunError as error:
            logger.warning(f"Error running overworld agent. Skipping. {error}")
