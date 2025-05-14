from emulator.emulator import YellowLegacyEmulator
from overworld_map.schemas import OverworldMap
from overworld_map.service import (
    add_remove_map_entities,
    get_overworld_map,
    update_overworld_map_tiles,
)


class UpdateCurrentMapService:
    """Service for updating the current map."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator

    async def update_current_map(self) -> OverworldMap:
        """Update the current overworld map with the latest screen info."""
        game_state = await self.emulator.get_game_state()
        current_map = await get_overworld_map(game_state)

        current_map = await add_remove_map_entities(game_state, current_map)
        return await update_overworld_map_tiles(game_state, current_map)
