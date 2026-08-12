"""Tests for the Sokoban solver service."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from agent.overworld.tools.sokoban_solver.service import SokobanSolverService
from common.enums import Button, SpriteLabel
from common.schemas import Coords
from emulator.emulator import Emulator
from memory.rolling_memory.schemas import RollingMemory
from overworld_map.service import prepare_overworld_map

if TYPE_CHECKING:
    from emulator.game_state import GameState


@pytest.mark.integration
async def test_solve_sokoban_puzzle_victory_road() -> None:
    """Test solving a Sokoban puzzle in Victory Road with pressure plates."""
    save_file = Path(__file__).parent / "saves" / "sokoban_victory_road.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=14, col=12)

        boulders = _get_boulders(game_state)
        assert len(boulders) == 1
        assert boulders == {Coords(row=14, col=14)}

        service = await _get_sokoban_service(emulator)
        await service.solve()

        game_state = await emulator.get_game_state()
        boulders = _get_boulders(game_state)
        assert len(boulders) == 1
        assert boulders == {Coords(row=13, col=17)}


@pytest.mark.integration
async def test_solve_sokoban_puzzle_seafoam_islands() -> None:
    """Test solving a Sokoban puzzle in Seafoam Islands with holes."""
    expected_num_boulders_before = 4
    expected_num_boulders_after = 2

    save_file = Path(__file__).parent / "saves" / "sokoban_seafoam.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=15, col=6)

        boulders = _get_boulders(game_state)
        assert len(boulders) == expected_num_boulders_before
        assert Coords(row=15, col=3) in boulders
        assert Coords(row=14, col=5) in boulders

        service = await _get_sokoban_service(emulator)
        await service.solve()

        # This one has two boulders to push, but we lose sight of the second one when we finish with
        # the first, so we have to walk back towards it.
        await emulator.press_button(Button.RIGHT)
        await emulator.press_button(Button.RIGHT)
        await emulator.press_button(Button.RIGHT)
        service = await _get_sokoban_service(emulator)  # Update the sprites.
        await service.solve()

        game_state = await emulator.get_game_state()
        boulders = _get_boulders(game_state)
        assert len(boulders) == expected_num_boulders_after
        assert Coords(row=14, col=2) in boulders
        assert Coords(row=12, col=9) in boulders


async def _get_sokoban_service(emulator: Emulator) -> SokobanSolverService:
    """Helper function to get a Sokoban solver service with the proper mocks."""
    game_state = await emulator.get_game_state()
    with (
        patch("overworld_map.service.get_map_memory", return_value=None),
        patch("overworld_map.service.get_visited_maps", return_value=[]),
        patch("overworld_map.service.create_map_memory", return_value=None),
        patch("overworld_map.service.update_map_terrain", return_value=None),
        patch("overworld_map.service._add_remove_map_entities", return_value=None),
    ):
        overworld_map = await prepare_overworld_map(0, game_state)
        overworld_map.known_sprite_ids = set(game_state.sprites)
    return SokobanSolverService(
        emulator=emulator,
        current_map=overworld_map,
        rolling_memory=RollingMemory(),
    )


def _get_boulders(game_state: GameState) -> set[Coords]:
    """Get the boulders from the game state."""
    return {
        s.coords
        for s in game_state.sprites.values()
        if s.label == SpriteLabel.BOULDER and s.is_rendered
    }
