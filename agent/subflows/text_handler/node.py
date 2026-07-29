"""Temporary Junjo adapter for text interactions."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.state import AgentStore
from agent.subflows.text_handler.agent import run_text_agent
from agent.subflows.text_handler.context import TextContext
from agent.subflows.text_handler.enums import TextHandler
from agent.subflows.text_handler.nodes.determine_handler.service import determine_handler
from agent.subflows.text_handler.nodes.handle_dialog_box.service import handle_dialog_box

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class TextHandlerNode(Node[AgentStore]):
    """Handle one text action from the root Junjo graph."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the text-handler adapter."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """Handle the current dialog, naming screen, or actionable text."""
        logger.info("Running the text handler...")

        state = await store.get_state()
        rolling_memory = state.rolling_memory
        handler = await determine_handler(self.emulator)
        if handler == TextHandler.DIALOG_BOX:
            rolling_memory = await handle_dialog_box(
                rolling_memory=rolling_memory,
                emulator=self.emulator,
            )
        elif handler in (TextHandler.NAME, TextHandler.GENERIC):
            context = TextContext(
                state=state,
                emulator=self.emulator,
            )
            try:
                await run_text_agent(context)
            except Exception as error:  # noqa: BLE001
                logger.warning(f"Error running text agent. Skipping. {error}")
            rolling_memory = context.state.rolling_memory

        await store.set_rolling_memory(rolling_memory)
