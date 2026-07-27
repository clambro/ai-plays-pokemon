"""Determine handler node for the text subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.text_handler.nodes.determine_handler.service import DetermineHandlerService
from agent.subflows.text_handler.state import TextHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class DetermineHandlerNode(Node[TextHandlerStore]):
    """Determine the handler to use."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the determine handler node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: TextHandlerStore) -> None:
        """The service for the node."""
        logger.info("Determining the handler...")

        service = DetermineHandlerService(emulator=self.emulator)
        handler = await service.determine_handler()

        await store.set_handler(handler)
