import asyncio
from emulator.emulator import YellowLegacyEmulator


class BuildAgentStateService:
    """Service for building the agent state."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator

    async def wait_for_movement_end(self) -> None:
        """Check if the player is moving, and if so, wait for them to stop."""
        while True:
            game_state = self.emulator.get_game_state()
            if not game_state.is_player_moving:
                break
            await asyncio.sleep(0.1)
