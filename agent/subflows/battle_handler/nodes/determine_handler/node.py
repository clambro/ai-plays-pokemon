"""Determine handler node for the battle subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.determine_handler.service import determine_handler
from agent.subflows.battle_handler.state import BattleHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class DetermineHandlerNode(Node[BattleHandlerStore]):
    """Determine the handler for the current game state in the battle."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the determine handler node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Determining the battle action...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")

        rolling_memory, tool_args = await determine_handler(
            rolling_memory=state.rolling_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )

        await store.set_rolling_memory(rolling_memory)
        await store.set_tool_args(tool_args)
