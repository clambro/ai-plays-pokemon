from emulator.emulator import YellowLegacyEmulator
from overworld_map.schemas import OverworldMap
from overworld_map.service import get_overworld_map


class LoadMapService:
    """Service for updating the current map."""

    def __init__(self, emulator: YellowLegacyEmulator, iteration: int) -> None:
        self.emulator = emulator
        self.iteration = iteration

    async def load_map(self) -> OverworldMap:
        """Update the current overworld map with the latest screen info."""
        game_state = self.emulator.get_game_state()
        return await get_overworld_map(self.iteration, game_state)
