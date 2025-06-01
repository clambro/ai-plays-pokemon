from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.should_critique.service import ShouldCritiqueService
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class ShouldCritiqueNode(Node):
    """A node that determines if the agent should critique the current state of the game."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Determining if the agent should critique the current state of the game...")

        state = await store.get_state()

        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.agent_memory is None:
            raise ValueError("Agent memory is not set")
        if state.goals is None:
            raise ValueError("Goals are not set")

        service = ShouldCritiqueService(
            iteration=state.iteration,
            agent_memory=state.agent_memory,
            goals=state.goals,
            emulator=self.emulator,
        )
        should_critique = await service.should_critique()
        await store.set_should_critique(should_critique)

        await store.set_emulator_save_state_from_emulator(self.emulator)
