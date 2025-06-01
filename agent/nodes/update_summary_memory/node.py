from junjo import Node
from loguru import logger

from agent.nodes.update_summary_memory.service import UpdateSummaryMemoryService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class UpdateSummaryMemoryNode(Node[AgentStore]):
    """Update the summary memory based on the current game state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Updating the summary memory...")

        state = await store.get_state()

        service = UpdateSummaryMemoryService(
            iteration=state.iteration,
            summary_memory=state.summary_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )
        summary_memory = await service.update_summary_memory()

        await store.set_summary_memory(summary_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
