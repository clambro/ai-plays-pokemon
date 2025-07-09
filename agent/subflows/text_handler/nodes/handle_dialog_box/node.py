from junjo import Node
from loguru import logger

from agent.subflows.text_handler.nodes.handle_dialog_box.service import HandleDialogBoxService
from agent.subflows.text_handler.state import TextHandlerStore
from emulator.emulator import YellowLegacyEmulator


class HandleDialogBoxNode(Node[TextHandlerStore]):
    """Handle reading the dialog box if it is present."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: TextHandlerStore) -> None:
        """The service for the node."""
        logger.info("Handling the dialog box if it is present...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")

        service = HandleDialogBoxService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            emulator=self.emulator,
        )
        raw_memory = await service.handle_dialog_box()

        await store.set_raw_memory(raw_memory)
