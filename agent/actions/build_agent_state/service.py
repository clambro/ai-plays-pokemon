import asyncio

from loguru import logger
from common.enums import StateHandler
from emulator.emulator import YellowLegacyEmulator


class BuildAgentStateService:
    """Service for building the agent state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator

    async def wait_for_animations(self) -> None:
        """Wait until all animations have finished so that we can begin the Agent loop."""
        successes = 0
        game_state = await self.emulator.get_game_state()
        while successes < 5:
            new_game_state = await self.emulator.get_game_state()
            if game_state.screen.tiles == new_game_state.screen.tiles:
                successes += 1
            else:
                successes = 0
                logger.info("Animation detected. Waiting for it to finish.")
            game_state = new_game_state
            await asyncio.sleep(0.02)

    async def determine_handler(self) -> StateHandler:
        """
        Determine which handler to use based on the current game state.

        :return: The handler to use.
        """
        game_state = await self.emulator.get_game_state()
        return StateHandler.BATTLE if game_state.battle.is_in_battle else StateHandler.OVERWORLD
