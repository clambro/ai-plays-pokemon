"""Create long term memory node for the top-level agent graph."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.nodes.create_long_term_memory.service import create_long_term_memory
from agent.state import AgentStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class CreateLongTermMemoryNode(Node[AgentStore]):
    """A node that creates long-term memory."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the create long term memory node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """The service for the node."""
        logger.info("Creating long-term memory if needed...")

        state = await store.get_state()

        await create_long_term_memory(
            iteration=state.iteration,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )
