"""Make decision node for the battle subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.agent import run_battle_decision
from agent.subflows.battle_handler.prepare import prepare_battle_context
from agent.subflows.battle_handler.state import BattleHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class MakeDecisionNode(Node[BattleHandlerStore]):
    """Run the battle agent for one action."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the make decision node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Running the battle agent for one action...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")
        if state.long_term_memory is None:
            raise ValueError("Long-term memory is not set")
        if state.goals is None:
            raise ValueError("Goals are not set")

        context = await prepare_battle_context(
            rolling_memory=state.rolling_memory,
            long_term_memory=state.long_term_memory,
            goals=state.goals,
            emulator=self.emulator,
        )
        try:
            await run_battle_decision(context)
        except Exception as error:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {error}")

        await store.set_rolling_memory(context.rolling_memory)
