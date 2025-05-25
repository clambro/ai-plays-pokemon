from junjo import Node
from loguru import logger

from agent.nodes.create_long_term_memory.service import CreateLongTermMemoryService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class CreateLongTermMemoryNode(Node[AgentStore]):
    """A node that creates long-term memory."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Creating long-term memory if needed...")

        state = await store.get_state()
        if not state.current_map:
            raise ValueError("Current map is not set.")

        service = CreateLongTermMemoryService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            goals=state.goals,
            emulator=self.emulator,
            summary_memory=state.summary_memory,
            long_term_memory=state.long_term_memory,
        )
        await service.create_long_term_memory()
