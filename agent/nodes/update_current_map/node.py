from junjo import Node
from loguru import logger

from agent.nodes.update_current_map.service import UpdateCurrentMapService
from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class UpdateCurrentMapNode(Node[AgentStore]):
    """Update the current map based on the current game state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Updating the current map...")

        state = await store.get_state()
        service = UpdateCurrentMapService(emulator=self.emulator, iteration=state.iteration)

        current_map = await service.update_current_map()

        await store.set_current_map(current_map)

        await store.set_emulator_save_state_from_emulator(self.emulator)
