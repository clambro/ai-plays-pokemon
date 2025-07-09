from junjo import Node
from loguru import logger

from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator


class SaveGameStateNode(Node[AgentStore]):
    """Save the game state to the AgentStore."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Saving the game state...")

        await store.set_emulator_save_state_from_emulator(self.emulator)
