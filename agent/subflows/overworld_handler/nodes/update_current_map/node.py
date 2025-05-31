from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.update_current_map.service import (
    UpdateCurrentMapService,
)
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class UpdateCurrentMapNode(Node[OverworldHandlerStore]):
    """Update the current map based on the current game state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Updating the current map...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        service = UpdateCurrentMapService(emulator=self.emulator, iteration=state.iteration)

        current_map = await service.update_current_map()

        await store.set_current_map(current_map)

        await store.set_emulator_save_state_from_emulator(self.emulator)

        await store.set_emulator_save_state_from_emulator(self.emulator)
