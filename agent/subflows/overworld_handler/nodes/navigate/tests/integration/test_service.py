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

        service = await _get_nav_service(emulator)

        service._determine_target_coords = AsyncMock(return_value=Coords(row=28, col=21))
        await service.navigate()

        game_state = emulator.get_game_state()
        assert game_state.player.coords == Coords(row=28, col=21)
        assert game_state.player.direction == FacingDirection.LEFT
        assert game_state.pikachu.coords == Coords(row=28, col=22)


@pytest.mark.integration
async def test_navigate_through_cut_tree() -> None:
    """Test rotating towards and navigating through a cut tree."""
    save_file = Path(__file__).parent / "saves" / "cut_tree.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = emulator.get_game_state()
        assert game_state.player.coords == Coords(row=17, col=17)

        service = await _get_nav_service(emulator)

        service._determine_target_coords = AsyncMock(return_value=Coords(row=20, col=15))
        await service.navigate()

        game_state = emulator.get_game_state()
        assert game_state.player.coords == Coords(row=20, col=15)


@pytest.mark.integration
async def test_navigate_through_spinners() -> None:
    """Test navigating through spinners."""
    save_file = Path(__file__).parent / "saves" / "rocket_spinners.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = emulator.get_game_state()
        assert game_state.player.coords == Coords(row=13, col=4)

        service = await _get_nav_service(emulator)

        service._determine_target_coords = AsyncMock(return_value=Coords(row=16, col=8))
        await service.navigate()

        game_state = emulator.get_game_state()
        assert game_state.player.coords == Coords(row=16, col=8)


async def _get_nav_service(emulator: YellowLegacyEmulator) -> NavigationService:
    """Helper function to get a navigation service with the proper mocks."""
    game_state = emulator.get_game_state()
    with (
        patch("database.map_memory.repository.get_map_memory", return_value=None),
        patch(
            "database.map_entity_memory.repository.get_map_entity_memories_for_map",
            return_value=[],
        ),
        patch("database.map_memory.repository.update_map_tiles", return_value=None),
        patch("overworld_map.service._add_remove_map_entities", return_value=None),
    ):
        overworld_map = await get_overworld_map(0, game_state)
        await update_map_with_screen_info(0, game_state, overworld_map)

    return NavigationService(
        iteration=0,
        emulator=emulator,
        current_map=overworld_map,
        raw_memory=RawMemory(),
        state_string_builder=MagicMock(),
    )
