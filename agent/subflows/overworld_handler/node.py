"""Temporary Junjo adapter for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.state import AgentStore
from agent.subflows.overworld_handler.agent import run_overworld

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class OverworldAgentNode(Node[AgentStore]):
    """Run one Pydantic AI overworld decision and action."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the overworld-agent node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """Run one overworld tool call and retain its mutable state."""
        logger.info("Running the overworld agent...")

        state = await store.get_state()
        try:
            await run_overworld(state, self.emulator)
        except Exception as error:  # noqa: BLE001
            logger.warning(f"Error running overworld agent. Skipping. {error}")

        await store.set_rolling_memory(state.rolling_memory)
