"""Update background stream node for the top-level agent graph."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.state import AgentStore
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class UpdateBackgroundStreamNode(Node[AgentStore]):
    """Update the background stream with the current state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the update background stream node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Updating the background stream...")

        state = await store.get_state()

        update_background_from_states(state, await self.emulator.get_game_state())
