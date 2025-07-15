from junjo import Node
from loguru import logger

from agent.subflows.overworld_handler.nodes.sokoban_solver.service import SokobanSolverService
from agent.subflows.overworld_handler.state import OverworldHandlerStore
from emulator.emulator import YellowLegacyEmulator


class SokobanSolverNode(Node[OverworldHandlerStore]):
    """Solve the Sokoban puzzle."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator
        super().__init__()

    async def service(self, store: OverworldHandlerStore) -> None:
        """The service for the node."""
        logger.info("Using the Sokoban solver...")

        state = await store.get_state()
        if state.iteration is None:
            raise ValueError("Iteration is not set")
        if state.raw_memory is None:
            raise ValueError("Raw memory is not set")
        if state.current_map is None:
            raise ValueError("Current map is not set")

        service = SokobanSolverService(
            iteration=state.iteration,
            emulator=self.emulator,
            current_map=state.current_map,
            raw_memory=state.raw_memory,
        )
        await service.solve()

        await store.set_raw_memory(state.raw_memory)
