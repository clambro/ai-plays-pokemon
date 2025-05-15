from emulator.emulator import YellowLegacyEmulator
from overworld_map.schemas import OverworldMap
from overworld_map.service import get_overworld_map, update_map_with_screen_info


class UpdateCurrentMapService:
    """Service for updating the current map."""

    def __init__(self, emulator: YellowLegacyEmulator, iteration: int) -> None:
        self.emulator = emulator
        self.iteration = iteration

    async def update_current_map(self) -> OverworldMap:
        """Update the current overworld map with the latest screen info."""
        game_state = await self.emulator.get_game_state()
        current_map = await get_overworld_map(self.iteration, game_state)
        return await update_map_with_screen_info(self.iteration, game_state, current_map)
