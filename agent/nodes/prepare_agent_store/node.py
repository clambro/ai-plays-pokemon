"""Prepare agent store node for the top-level agent graph."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.nodes.prepare_agent_store.service import (
    determine_handler,
    wait_for_animations,
)
from agent.state import AgentStore
from memory.long_term_memory import LongTermMemory
from memory.rolling_memory import initialize_memory
from streaming.server import update_background_log_from_memory

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class PrepareAgentStoreNode(Node[AgentStore]):
    """Prepare the agent store for its next iteration.

    This first node selects the appropriate handler and initializes rolling memory.
    """

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the prepare agent store node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Preparing agent store...")

        state = await store.get_state()
        await wait_for_animations(self.emulator)
        handler = await determine_handler(self.emulator)
        rolling_memory = await initialize_memory(state.rolling_memory.current_block)

        await store.set_iteration(rolling_memory.current_block.iteration)
        await store.set_rolling_memory(rolling_memory)
        if rolling_memory.current_block.iteration != state.iteration:
            await store.set_long_term_memory(LongTermMemory())
        update_background_log_from_memory(rolling_memory)
        await store.set_handler(handler)
