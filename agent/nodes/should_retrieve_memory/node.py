from junjo import Node
from loguru import logger

from agent.nodes.should_retrieve_memory.service import ShouldRetrieveMemoryService
from agent.state import AgentStore


class ShouldRetrieveMemoryNode(Node[AgentStore]):
    """A node that checks if the agent should retrieve memory."""

    def __init__(self) -> None:
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Checking if the agent should retrieve memory...")

        state = await store.get_state()
        if state.handler is None:
            raise RuntimeError("Handler is not set")

        service = ShouldRetrieveMemoryService(
            iteration=state.iteration,
            handler=state.handler,
            previous_handler=state.previous_handler,
            long_term_memory=state.long_term_memory,
        )
        should_retrieve_memory = await service.should_retrieve_memory()

        await store.set_should_retrieve_memory(should_retrieve_memory)
