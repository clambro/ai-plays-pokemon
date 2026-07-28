"""Throw ball tool node for the battle subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.throw_ball_tool.service import throw_ball
from agent.subflows.battle_handler.schemas import ThrowBallToolArgs
from agent.subflows.battle_handler.state import BattleHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class ThrowBallToolNode(Node[BattleHandlerStore]):
    """Throw a ball at the enemy."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the throw ball tool node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Throwing a ball at the enemy...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")
        if not isinstance(state.tool_args, ThrowBallToolArgs):
            raise TypeError("Tool args is not a ThrowBallToolArgs")

        rolling_memory = await throw_ball(
            rolling_memory=state.rolling_memory,
            tool_args=state.tool_args,
            emulator=self.emulator,
        )

        await store.set_rolling_memory(rolling_memory)
