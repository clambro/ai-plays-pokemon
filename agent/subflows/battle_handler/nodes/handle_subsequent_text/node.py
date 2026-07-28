"""Handle subsequent text node for the battle subflow."""

from typing import TYPE_CHECKING

from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.handle_subsequent_text.service import (
    handle_subsequent_text,
)
from agent.subflows.battle_handler.state import BattleHandlerStore

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator


class HandleSubsequentTextNode(Node[BattleHandlerStore]):
    """Handles reading the subsequent text (if present) after a tool has been used."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        """Initialize the handle subsequent text node."""
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Handling the subsequent text if it is present...")

        state = await store.get_state()
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")

        rolling_memory = await handle_subsequent_text(
            rolling_memory=state.rolling_memory,
            emulator=self.emulator,
        )

        await store.set_rolling_memory(rolling_memory)
