"""Temporary Junjo adapter for the Pydantic AI overworld agent."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.agent import run_overworld
from agent.subflows.overworld_handler.context import OverworldContext
from agent.subflows.overworld_handler.state import OverworldHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class OverworldAgentNode(Node[OverworldHandlerStore]):
    """Run one Pydantic AI overworld decision and action."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the overworld-agent node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """Run one overworld tool call and retain its mutable state."""
        logger.info("Running the overworld agent...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")
        if state.current_map is None:
            raise ValueError("Current map is not set")

        context = OverworldContext(
            state=state,
            emulator=self.emulator,
        )
        try:
            await run_overworld(context)
        except Exception as error:  # noqa: BLE001
            logger.warning(f"Error running overworld agent. Skipping. {error}")

        if context.state.current_map is None:
            raise ValueError("Current map is not set")
        if context.state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")
        await store.set_current_map(context.state.current_map)
        await store.set_rolling_memory(context.state.rolling_memory)
