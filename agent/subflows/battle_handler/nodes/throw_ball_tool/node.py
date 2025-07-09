from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.throw_ball_tool.service import ThrowBallToolService
from agent.subflows.battle_handler.schemas import ThrowBallToolArgs
from agent.subflows.battle_handler.state import BattleHandlerStore
from emulator.emulator import YellowLegacyEmulator


class ThrowBallToolNode(Node[BattleHandlerStore]):
    """Throw a ball at the enemy."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Throwing a ball at the enemy...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")
        if not isinstance(state.tool_args, ThrowBallToolArgs):
            raise TypeError("Tool args is not a ThrowBallToolArgs")

        service = ThrowBallToolService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            tool_args=state.tool_args,
            emulator=self.emulator,
        )

        raw_memory = await service.throw_ball()

        await store.set_raw_memory(raw_memory)
