from junjo import Node
from loguru import logger

from agent.nodes.update_long_term_memory.service import UpdateLongTermMemoryService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class UpdateLongTermMemoryNode(Node[AgentStore]):
    """A node that updates long-term memory."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Updating long-term memory...")

        state = await store.get_state()

        service = UpdateLongTermMemoryService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            goals=state.goals,
            emulator=self.emulator,
            summary_memory=state.summary_memory,
            long_term_memory=state.long_term_memory,
        )
        await service.update_long_term_memory()

        await store.set_emulator_save_state_from_emulator(self.emulator)
