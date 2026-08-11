"""Tests for the navigate service."""

from pathlib import Path
from unittest.mock import patch

import pytest

from agent.overworld.tools.navigate.service import NavigationService
from common.enums import FacingDirection
from common.schemas import Coords
from emulator.emulator import Emulator
from memory.rolling_memory.schemas import RollingMemory
from overworld_map.service import prepare_overworld_map


@pytest.mark.integration
async def test_navigate_through_pikachu() -> None:
    """Test navigating through Pikachu."""
    save_file = Path(__file__).parent / "saves" / "viridian.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=28, col=23)
        assert game_state.pikachu.coords == Coords(row=28, col=22)
        assert game_state.player.direction == FacingDirection.RIGHT

        service = await _get_nav_service(emulator)

        await service.navigate(Coords(row=28, col=21))

        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=28, col=21)
        assert game_state.player.direction == FacingDirection.LEFT
        assert game_state.pikachu.coords == Coords(row=28, col=22)


@pytest.mark.integration
async def test_navigate_through_cut_tree() -> None:
    """Test rotating towards and navigating through a cut tree."""
    save_file = Path(__file__).parent / "saves" / "cut_tree.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=17, col=17)

        service = await _get_nav_service(emulator)

        await service.navigate(Coords(row=20, col=15))

        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=20, col=15)


@pytest.mark.integration
async def test_navigate_through_spinners() -> None:
    """Test navigating through spinners."""
    save_file = Path(__file__).parent / "saves" / "rocket_spinners.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=13, col=4)

        service = await _get_nav_service(emulator)

        await service.navigate(Coords(row=16, col=8))

        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=16, col=8)


@pytest.mark.integration
async def test_navigate_through_water() -> None:
    """Test navigating through water."""
    save_file = Path(__file__).parent / "saves" / "celadon_water.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=20, col=19)

        service = await _get_nav_service(emulator)

        await service.navigate(Coords(row=16, col=21))

        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=16, col=21)


async def _get_nav_service(emulator: Emulator) -> NavigationService:
    """Helper function to get a navigation service with the proper mocks."""
    game_state = await emulator.get_game_state()
    with (
        patch("database.map_memory.repository.get_map_memory", return_value=None),
        patch(
            "database.map_entity_memory.repository.get_map_entity_memories_for_map",
            return_value=[],
        ),
        patch("database.map_memory.repository.update_map_tiles", return_value=None),
        patch("overworld_map.service._add_remove_map_entities", return_value=None),
    ):
        overworld_map = await prepare_overworld_map(0, game_state)

    return NavigationService(
        iteration=0,
        emulator=emulator,
        current_map=overworld_map,
        rolling_memory=RollingMemory(),
    )
