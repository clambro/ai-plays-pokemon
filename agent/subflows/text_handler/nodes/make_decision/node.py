"""Make decision node for the text subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.text_handler.nodes.make_decision.service import make_decision
from agent.subflows.text_handler.state import TextHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class MakeDecisionNode(Node[TextHandlerStore]):
    """Make a decision based on the current game state in the text."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the make decision node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: TextHandlerStore) -> None:
        """The service for the node."""
        logger.info("Running the text decision maker...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")

        rolling_memory = await make_decision(
            rolling_memory=state.rolling_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )

        await store.set_rolling_memory(rolling_memory)
