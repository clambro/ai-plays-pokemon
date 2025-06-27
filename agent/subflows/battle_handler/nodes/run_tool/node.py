from junjo import Node
from loguru import logger

from agent.subflows.battle_handler.nodes.run_tool.service import RunToolService
from agent.subflows.battle_handler.state import BattleHandlerStore
from emulator.emulator import YellowLegacyEmulator


class RunToolNode(Node[BattleHandlerStore]):
    """Run away from the battle."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: BattleHandlerStore) -> None:
        """The service for the node."""
        logger.info("Running the run tool...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")

        service = RunToolService(
            iteration=state.iteration,
            raw_memory=state.raw_memory,
            emulator=self.emulator,
        )

        raw_memory = await service.run_away()

        await store.set_raw_memory(raw_memory)
        await store.set_emulator_save_state_from_emulator(self.emulator)
