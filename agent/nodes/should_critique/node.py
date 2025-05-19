from junjo import Node
from loguru import logger

from agent.nodes.should_critique.service import ShouldCritiqueService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class ShouldCritiqueNode(Node):
    """A node that determines if the agent should critique the current state of the game."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Determining if the agent should critique the current state of the game...")

        state = await store.get_state()
        if not state.current_map:
            raise ValueError("Current map is not set.")

        service = ShouldCritiqueService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            current_map=state.current_map,
            goals=state.goals,
            emulator=self.emulator,
        )
        should_critique = await service.should_critique()
        await store.set_should_critique(should_critique)
