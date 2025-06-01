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
            iteration=state.iteration,
            long_term_memory=state.long_term_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )
        long_term_memory = await service.retrieve_long_term_memory()

        await store.set_long_term_memory(long_term_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
