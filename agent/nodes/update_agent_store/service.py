from common.enums import AgentStateHandler
from emulator.emulator import YellowLegacyEmulator


class BuildAgentStateService:
    """Service for building the agent state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator

    async def wait_for_animations(self) -> None:
        """Wait until all animations have finished so that we can begin the Agent loop."""
        return await self.emulator.wait_for_animation_to_finish()

    async def determine_handler(self) -> AgentStateHandler:
        """
        Determine which handler to use based on the current game state.

        :return: The handler to use.
        """
        game_state = self.emulator.get_game_state()
        if game_state.battle.is_in_battle:
            return AgentStateHandler.BATTLE
        elif (
            game_state.is_text_on_screen()
            or game_state.cur_map.height == 0
            or game_state.cur_map.width == 0
        ):
            return AgentStateHandler.TEXT
        else:
            return AgentStateHandler.OVERWORLD
