"""Temporary Junjo adapter for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger
from pydantic_ai import AgentRunError

from agent.state import AgentStore
from agent.subflows.overworld_handler.agent import run_overworld

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class OverworldAgentNode(Node[AgentStore]):
    """Run one Pydantic AI overworld conversation."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the overworld-agent node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """Run the overworld agent and retain its mutable state."""
        logger.info("Running the overworld agent...")

        state = await store.get_state()
        try:
            await run_overworld(state, self.emulator)
        except AgentRunError as error:
            logger.warning(f"Error running overworld agent. Skipping. {error}")

        await store.set_rolling_memory(state.rolling_memory)
        await store.set_long_term_memory(state.long_term_memory)
        await store.set_goals(state.goals)
