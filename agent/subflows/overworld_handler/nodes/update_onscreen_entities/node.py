from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.update_onscreen_entities.service import (
    UpdateOnscreenEntitiesService,
)
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class UpdateOnscreenEntitiesNode(Node[OverworldHandlerStore]):
    """Update the onscreen entities based on the current game state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Updating the onscreen entities...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.agent_memory is None:
            raise ValueError("Agent memory is not set")
        if state.current_map is None:
            raise ValueError("Current map is not set.")

        service = UpdateOnscreenEntitiesService(
            emulator=self.emulator,
            iteration=state.iteration,
            agent_memory=state.agent_memory,
            current_map=state.current_map,
        )
        await service.update_onscreen_entities()

        await store.set_emulator_save_state_from_emulator(self.emulator)
