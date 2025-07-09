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
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")

        service = CritiqueService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )
        raw_memory = await service.critique()

        await store.set_raw_memory(raw_memory)
        await store.set_iterations_since_last_critique(0)
