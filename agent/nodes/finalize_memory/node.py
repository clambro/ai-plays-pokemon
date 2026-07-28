"""Finalize rolling memory at the end of a top-level workflow."""

from junjo import Node
from loguru import logger

from agent.state import AgentStore
from memory.rolling_memory import finalize_iteration


class FinalizeMemoryNode(Node[AgentStore]):
    """Persist and compact the completed iteration's memory."""

    async def service(self, store: AgentStore) -> None:
        """Finalize the current rolling-memory block."""
        logger.info("Finalizing rolling memory...")

        state = await store.get_state()
        await finalize_iteration(state.rolling_memory)
