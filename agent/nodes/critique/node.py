from junjo import Node
from loguru import logger

from agent.nodes.critique.service import CritiqueService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class CritiqueNode(Node[AgentStore]):
    """A node that critiques the current state of the game."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Critiquing the current state of the game...")

        state = await store.get_state()
        if not state.current_map:
            raise ValueError("Current map is not set.")

        service = CritiqueService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            current_map=state.current_map,
            goals=state.goals,
            emulator=self.emulator,
            summary_memory=state.summary_memory,
            long_term_memory=state.long_term_memory,
        )
        await service.critique()

        await store.set_raw_memory(service.raw_memory)
