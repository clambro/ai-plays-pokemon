from pathlib import Path

from emulator.emulator import YellowLegacyEmulator
from overworld_map.schemas import OverworldMap


class UpdateCurrentMapService:
    """Service for updating the current map."""

    def __init__(self, emulator: YellowLegacyEmulator, folder: Path) -> None:
        self.emulator = emulator
        self.folder = folder

    async def update_current_map(self) -> OverworldMap:
        """
        Load the current map from the emulator, update it with the latest screen info, save it,
        and return it.
        """
        game_state = await self.emulator.get_game_state()
        try:
            current_map = await OverworldMap.load(self.folder, game_state.cur_map.id)
        except FileNotFoundError:
            current_map = await OverworldMap.from_game_state(self.folder, game_state)

        current_map.update_with_screen_info(game_state)
        await current_map.save(self.folder)
        return current_map
