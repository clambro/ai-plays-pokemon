from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory
from overworld_map.schemas import OverworldMap


class SokobanSolverService:
    """Solve the Sokoban puzzle."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        current_map: OverworldMap,
        raw_memory: RawMemory,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.current_map = current_map
        self.raw_memory = raw_memory

    async def solve(self) -> None:
        """Solve the Sokoban puzzle."""
