from junjo import Node
from loguru import logger

from agent.nodes.load_long_term_memory.service import LoadLongTermMemoryService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


# Temporary until we have RAG set up.
class LoadLongTermMemoryNode(Node[AgentStore]):
    """Load the entire long-term memory from the database."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Loading long-term memory...")

        state = await store.get_state()

        service = LoadLongTermMemoryService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            summary_memory=state.summary_memory,
            last_long_term_memory=state.long_term_memory,
        )
        ltm = await service.load_long_term_memory()

        await store.set_long_term_memory(ltm)
