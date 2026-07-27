"""Fight tool node for the battle subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.fight_tool.service import fight
from agent.subflows.battle_handler.schemas import FightToolArgs
from agent.subflows.battle_handler.state import BattleHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class FightToolNode(Node[BattleHandlerStore]):
    """Use a move on the enemy."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the fight tool node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Using a move on the enemy...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")
        if not isinstance(state.tool_args, FightToolArgs):
            raise TypeError("Tool args is not a UseMoveToolArgs")

        raw_memory = await fight(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            tool_args=state.tool_args,
            emulator=self.emulator,
        )

        await store.set_raw_memory(raw_memory)
