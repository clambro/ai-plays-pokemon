"""Handle dialog box node for the text subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.text_handler.nodes.handle_dialog_box.service import handle_dialog_box
from agent.subflows.text_handler.state import TextHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class HandleDialogBoxNode(Node[TextHandlerStore]):
    """Handle reading the dialog box if it is present."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the handle dialog box node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: TextHandlerStore) -> None:
        """The service for the node."""
        logger.info("Handling the dialog box if it is present...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")

        rolling_memory = await handle_dialog_box(
            rolling_memory=state.rolling_memory,
            emulator=self.emulator,
        )

        await store.set_rolling_memory(rolling_memory)
