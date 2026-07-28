"""Run tool node for the battle subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.run_tool.service import run_away
from agent.subflows.battle_handler.schemas import RunToolArgs
from agent.subflows.battle_handler.state import BattleHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class RunToolNode(Node[BattleHandlerStore]):
    """Run away from the battle."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the run tool node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Running the run tool...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")
        if not isinstance(state.tool_args, RunToolArgs):
            raise TypeError("Tool args is not a RunToolArgs")

        rolling_memory = await run_away(
            rolling_memory=state.rolling_memory,
            emulator=self.emulator,
        )

        await store.set_rolling_memory(rolling_memory)
