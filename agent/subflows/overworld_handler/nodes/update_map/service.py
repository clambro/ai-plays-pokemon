"""Business logic for update map in the overworld subflow."""

from typing import TYPE_CHECKING

from overworld_map.service import update_map_with_screen_info

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from overworld_map.schemas import OverworldMap


async def update_map(
    *,
    iteration: int,
    current_map: OverworldMap,
    emulator: YellowLegacyEmulator,
) -> OverworldMap:
    """Update explored terrain from the visible screen.

    Args:
        iteration: Current agent iteration used to timestamp map-memory updates.
        current_map: Explored map to update from the visible screen.
        emulator: Running emulator used to inspect the current game state.

    Returns:
        The updated explored map.
    """
    game_state = await emulator.get_game_state()
    return await update_map_with_screen_info(iteration, game_state, current_map)
