"""Temporary Junjo adapter for the Pydantic AI battle agent."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger
from pydantic_ai import AgentRunError

from agent.state import AgentStore
from agent.subflows.battle_handler.agent import run_battle

if TYPE_CHECKING:
    from agent.context import AgentContext


class BattleAgentNode(Node[AgentStore]):
    """Run the Pydantic AI agent for the complete battle."""

    def __init__(self, context: AgentContext) -> None:
        """Initialize the battle-agent node."""
        self.context = context
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """Run the complete battle loop through the shared context."""
        del store
        logger.info("Running the battle agent...")

        try:
            await run_battle(self.context)
        except AgentRunError as error:
            logger.warning(f"Error running battle agent. Skipping. {error}")
