from common.enums import StateHandler
from emulator.emulator import YellowLegacyEmulator


class DetermineHandlerService:
    """A service that determines which handler to use based on the current game state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator

    async def determine_handler(self) -> StateHandler:
        """
        Determine which handler to use based on the current game state.

        :return: The handler to use.
        """
        game_state = self.emulator.get_game_state()
        return StateHandler.BATTLE if game_state.battle.is_in_battle else StateHandler.OVERWORLD
