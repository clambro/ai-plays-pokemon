from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.determine_handler.service import DetermineHandlerService
from agent.subflows.battle_handler.state import BattleHandlerStore
from emulator.emulator import YellowLegacyEmulator


class DetermineHandlerNode(Node[BattleHandlerStore]):
    """Determine the handler for the current game state in the battle."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Determining the battle action...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")

        service = DetermineHandlerService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            state_string_builder=state.to_prompt_string,
            emulator=self.emulator,
        )

        raw_memory, tool_args = await service.determine_handler()

        await store.set_raw_memory(raw_memory)
        await store.set_tool_args(tool_args)
        await store.set_emulator_save_state_from_emulator(self.emulator)
