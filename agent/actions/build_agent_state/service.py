import asyncio

from loguru import logger
from emulator.emulator import YellowLegacyEmulator


class BuildAgentStateService:
    """Service for building the agent state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator

    async def wait_for_movement_end(self) -> None:
        """
        Check if the player is moving, and if so, wait for them to stop.

        This is to ensure that the player is not moving when the agent loop starts. We need to run
        the check a few times to ensure that we didn't just catch the player between animation
        frames.
        """
        successes = 0
        while True:
            game_state = self.emulator.get_game_state()
            if game_state.is_player_moving:
                successes = 0
                logger.info("Player movement detected. Waiting for it to end.")
            else:
                successes += 1
            if successes >= 3:
                break
            await asyncio.sleep(0.01)
