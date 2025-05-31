from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.critique.service import CritiqueService
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class CritiqueNode(Node[OverworldHandlerStore]):
    """A node that critiques the current state of the game."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Critiquing the current state of the game...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.agent_memory is None:
            raise ValueError("Agent memory is not set")
        if state.current_map is None:
            raise ValueError("Current map is not set")
        if state.goals is None:
            raise ValueError("Goals are not set")

        service = CritiqueService(
            iteration=state.iteration,
            agent_memory=state.agent_memory,
            current_map=state.current_map,
            goals=state.goals,
            emulator=self.emulator,
        )
        agent_memory = await service.critique()

        await store.set_agent_memory(agent_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
