from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.subflows.overworld_handler.nodes.navigate.service import NavigationService
from common.enums import FacingDirection
from common.schemas import Coords
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory
from overworld_map.service import get_overworld_map, update_map_with_screen_info


@pytest.mark.integration
async def test_navigate_through_pikachu() -> None:
    """Test navigating through Pikachu."""
    save_file = Path(__file__).parent / "saves" / "viridian.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = emulator.get_game_state()
        assert game_state.player.coords == Coords(row=28, col=23)
        assert game_state.pikachu.coords == Coords(row=28, col=22)
        assert game_state.player.direction == FacingDirection.RIGHT

        with (
            patch("database.map_memory.repository.get_map_memory", return_value=None),
            patch(
                "database.map_entity_memory.repository.get_map_entity_memories_for_map",
                return_value=[],
            ),
            patch("database.map_memory.repository.update_map_tiles", return_value=None),
        ):
            overworld_map = await get_overworld_map(0, game_state)
            await update_map_with_screen_info(0, game_state, overworld_map)

        service = NavigationService(
            iteration=0,
            emulator=emulator,
            current_map=overworld_map,
            raw_memory=RawMemory(),
            state_string_builder=MagicMock(),
        )

        service._determine_target_coords = AsyncMock(return_value=Coords(row=28, col=21))
        overworld_map, raw_memory = await service.navigate()

        game_state = emulator.get_game_state()
        assert game_state.player.coords == Coords(row=28, col=21)
        assert game_state.player.direction == FacingDirection.LEFT
        assert game_state.pikachu.coords == Coords(row=28, col=22)
