from junjo import Node
from loguru import logger

from agent.nodes.retrieve_long_term_memory.service import RetrieveLongTermMemoryService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class RetrieveLongTermMemoryNode(Node[AgentStore]):
    """Retrieve the long-term memory from the database."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Retrieving the long-term memory...")

        state = await store.get_state()

        service = RetrieveLongTermMemoryService(
            emulator=self.emulator,
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            summary_memory=state.summary_memory,
            prev_long_term_memory=state.long_term_memory,
            goals=state.goals,
        )
        ltm = await service.retrieve_long_term_memory()

        await store.set_long_term_memory(ltm)

        await store.set_emulator_save_state_from_emulator(self.emulator)
