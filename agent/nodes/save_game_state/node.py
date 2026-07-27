"""Save game state node for the top-level agent graph."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.state import AgentStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class SaveGameStateNode(Node[AgentStore]):
    """Save the game state to the AgentStore."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the save game state node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Saving the game state...")

        await store.set_emulator_save_state_from_emulator(self.emulator)
