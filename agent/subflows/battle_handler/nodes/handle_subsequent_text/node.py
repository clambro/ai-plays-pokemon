from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.handle_subsequent_text.service import (
    HandleSubsequentTextService,
)
from agent.subflows.battle_handler.state import BattleHandlerStore
from emulator.emulator import YellowLegacyEmulator


class HandleSubsequentTextNode(Node[BattleHandlerStore]):
    """Handles reading the subsequent text (if present) after a tool has been used."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Handling the subsequent text if it is present...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")

        service = HandleSubsequentTextService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            emulator=self.emulator,
        )
        raw_memory = await service.handle_subsequent_text()

        await store.set_raw_memory(raw_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
