"""Temporary Junjo adapter for text interactions."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.context import AgentContext
from agent.state import AgentStore
from agent.subflows.text_handler.agent import run_text

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class TextHandlerNode(Node[AgentStore]):
    """Run one complete text interaction from the root Junjo graph."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the text-handler adapter."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """Handle the current dialog and any decisions it reveals."""
        logger.info("Running the text handler...")

        state = await store.get_state()
        context = AgentContext(
            state=state,
            emulator=self.emulator,
        )
        try:
            await run_text(context)
        except Exception as error:  # noqa: BLE001
            logger.warning(f"Error running text interaction. Skipping. {error}")

        await store.set_rolling_memory(context.state.rolling_memory)
