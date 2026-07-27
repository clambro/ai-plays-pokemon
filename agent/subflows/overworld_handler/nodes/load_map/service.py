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
    """Update the current overworld map with the latest screen info."""
    game_state = emulator.get_game_state()
    return await get_overworld_map(iteration, game_state)
