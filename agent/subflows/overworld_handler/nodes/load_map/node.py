from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.load_map.service import LoadMapService
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class LoadMapNode(Node[OverworldHandlerStore]):
    """Load the current map based on the game state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Loading the current map...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        service = LoadMapService(emulator=self.emulator, iteration=state.iteration)

        current_map = await service.load_map()

        await store.set_current_map(current_map)
        await store.set_emulator_save_state_from_emulator(self.emulator)
