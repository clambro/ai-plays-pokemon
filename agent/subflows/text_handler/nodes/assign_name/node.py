"""Assign name node for the text subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.text_handler.nodes.assign_name.service import AssignNameService
from agent.subflows.text_handler.state import TextHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class AssignNameNode(Node[TextHandlerStore]):
    """Assign a name to something in the game."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the assign name node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: TextHandlerStore) -> None:
        """The service for the node."""
        logger.info("Assigning a name...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")

        service = AssignNameService(
            rolling_memory=state.rolling_memory,
            emulator=self.emulator,
        )
        rolling_memory = await service.assign_name()

        await store.set_rolling_memory(rolling_memory)
