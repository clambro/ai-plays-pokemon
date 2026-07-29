"""Temporary Junjo adapter for the Pydantic AI battle agent."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.state import AgentStore
from agent.subflows.battle_handler.agent import run_battle
from agent.subflows.battle_handler.prepare import prepare_battle_context

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class BattleAgentNode(Node[AgentStore]):
    """Run the Pydantic AI agent for the complete battle."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the battle-agent node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: AgentStore) -> None:
        """Run the complete battle loop and retain its rolling memory."""
        logger.info("Running the battle agent...")

        state = await store.get_state()
        context = await prepare_battle_context(
            state=state,
            emulator=self.emulator,
        )
        try:
            await run_battle(context)
        except Exception as error:  # noqa: BLE001
            logger.warning(f"Error running battle agent. Skipping. {error}")

        await store.set_rolling_memory(context.state.rolling_memory)
