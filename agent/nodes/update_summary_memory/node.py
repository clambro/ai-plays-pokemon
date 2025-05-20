from junjo import Node
from loguru import logger

from agent.nodes.update_summary_memory.service import UpdateSummaryMemoryService
from agent.state import AgentStore


class UpdateSummaryMemoryNode(Node[AgentStore]):
    """Update the summary memory based on the current game state."""

    def __init__(self) -> None:
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Updating the summary memory...")

        state = await store.get_state()
        if state.current_map is None:
            raise ValueError("Current map is not set.")

        service = UpdateSummaryMemoryService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            summary_memory=state.summary_memory,
            current_map=state.current_map,
        )
        await service.update_summary_memory()
        await store.set_summary_memory(service.summary_memory)
