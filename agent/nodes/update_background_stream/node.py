from junjo import Node
from loguru import logger

from agent.state import AgentStore
from emulator.emulator import YellowLegacyEmulator
from streaming.server import update_background_from_states


class UpdateBackgroundStreamNode(Node[AgentStore]):
    """Update the background stream with the current state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Updating the background stream...")

        state = await store.get_state()

        await update_background_from_states(state, self.emulator.get_game_state())
