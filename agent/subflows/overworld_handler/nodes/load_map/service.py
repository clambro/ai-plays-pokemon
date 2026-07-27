"""Business logic for load map in the overworld subflow."""

from typing import TYPE_CHECKING

from overworld_map.service import get_overworld_map

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from overworld_map.schemas import OverworldMap


async def load_map(
    emulator: YellowLegacyEmulator,
    iteration: int,
) -> OverworldMap:
    """Load or create the explored map for the current game state.

    Args:
        emulator: Running emulator used to inspect the current map.
        iteration: Current agent iteration used when creating map memory.

    Returns:
        The explored-map snapshot for the current location.
    """
    game_state = await emulator.get_game_state()
    return await get_overworld_map(iteration, game_state)
