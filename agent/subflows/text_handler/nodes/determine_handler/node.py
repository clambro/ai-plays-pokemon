from junjo import Node
from loguru import logger

from agent.subflows.text_handler.nodes.determine_handler.service import DetermineHandlerService
from agent.subflows.text_handler.state import TextHandlerStore
from emulator.emulator import YellowLegacyEmulator


class DetermineHandlerNode(Node[TextHandlerStore]):
    """Determine the handler to use."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: TextHandlerStore) -> None:
        """The service for the node."""
        logger.info("Determining the handler...")

        service = DetermineHandlerService(emulator=self.emulator)
        handler = await service.determine_handler()

        await store.set_handler(handler)
        await store.set_emulator_save_state_from_emulator(self.emulator)
