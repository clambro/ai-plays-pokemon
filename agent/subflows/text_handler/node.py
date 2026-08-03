"""Temporary Junjo adapter for text interactions."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger
from pydantic_ai import AgentRunError

from agent.state import AgentStore
from agent.subflows.text_handler.agent import run_text

if TYPE_CHECKING:
    from agent.context import AgentContext


class TextHandlerNode(Node[AgentStore]):
    """Run one complete text interaction from the root Junjo graph."""

    def __init__(self, context: AgentContext) -> None:
        """Initialize the text-handler adapter."""
        self.context = context
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """Handle the current dialog and any decisions it reveals."""
        del store
        logger.info("Running the text handler...")

        try:
            await run_text(self.context)
        except AgentRunError as error:
            logger.warning(f"Error running text interaction. Skipping. {error}")
