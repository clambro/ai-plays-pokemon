"""Tests for the navigate service."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from agent.overworld.tools.navigate.service import NavigationService
from common.enums import AsciiTile, Button, FacingDirection
from common.schemas import Coords
from emulator.emulator import Emulator
from memory.rolling_memory.schemas import RollingMemory
from overworld_map.service import prepare_overworld_map

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _isolate_map_memory() -> Iterator[None]:
    with (
        patch("overworld_map.service.get_map_memory", return_value=None),
        patch("overworld_map.service.get_map_entity_memories_for_map", return_value=[]),
        patch("overworld_map.service.get_visited_maps", return_value=[]),
        patch("overworld_map.service.create_map_memory", return_value=None),
        patch("overworld_map.service.update_map_terrain", return_value=None),
        patch("overworld_map.service.apply_map_entity_changes", return_value=None),
    ):
        yield


@pytest.mark.integration
async def test_navigate_after_turning() -> None:
    """Complete the first movement step after changing direction."""
    save_file = Path(__file__).parent / "saves" / "viridian.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        service = await _get_nav_service(emulator)

        await service.navigate(Coords(row=30, col=23))

        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=30, col=23)
        assert game_state.player.direction == FacingDirection.DOWN


@pytest.mark.integration
async def test_navigate_through_pikachu_while_facing_it() -> None:
    """Preserve the requested steps while Pikachu yields to the player."""
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

        await emulator.press_overworld_button(Button.LEFT)
        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=28, col=23)
        assert game_state.player.direction == FacingDirection.LEFT

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
async def test_navigate_to_cut_tree_refreshes_removed_terrain() -> None:
    """Refresh the map when Cut reaches the target on the field-move step."""
    save_file = Path(__file__).parent / "saves" / "cut_tree.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=17, col=17)

        service = await _get_nav_service(emulator)
        target = Coords(row=18, col=15)
        assert service.current_map.terrain[target.row][target.col] == AsciiTile.CUT_TREE

        await service.navigate(target)

        game_state = await emulator.get_game_state()
        assert game_state.player.coords == target
        assert service.current_map.terrain[target.row][target.col] == AsciiTile.FREE


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
    overworld_map = await prepare_overworld_map(0, game_state)

    return NavigationService(
        iteration=0,
        emulator=emulator,
        current_map=overworld_map,
        rolling_memory=RollingMemory(),
    )
