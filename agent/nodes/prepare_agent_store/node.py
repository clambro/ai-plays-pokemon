"""Prepare agent store node for the top-level agent graph."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.nodes.prepare_agent_store.service import (
    determine_handler,
    wait_for_animations,
)
from agent.state import AgentStore

if TYPE_CHECKING:
    from agent.context import AgentContext


class PrepareAgentStoreNode(Node[AgentStore]):
    """Select the handler for the temporary Junjo routing graph."""

    def __init__(self, context: AgentContext) -> None:
        """Initialize the prepare agent store node."""
        self.context = context
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Preparing agent store...")

        await wait_for_animations(self.context.emulator)
        handler = await determine_handler(self.context.emulator)
        self.context.state.handler = handler
        await store.set_handler(handler)
