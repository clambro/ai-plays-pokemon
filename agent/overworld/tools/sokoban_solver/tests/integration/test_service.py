"""Tests for the Sokoban solver service."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from agent.overworld.tools.sokoban_solver.service import solve_sokoban
from common.enums import SpriteLabel
from common.schemas import Coords
from emulator.emulator import Emulator
from memory.rolling_memory.schemas import RollingMemory
from overworld_map.service import prepare_overworld_map

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pyboy import PyBoy

    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap

_NO_RANDOM_BATTLE_STEPS_ADDRESS = 0xD13B
_MAX_BYTE = 0xFF


@pytest.fixture(autouse=True)
def _isolated_map_memory() -> Iterator[None]:
    """Keep emulator tests independent of the live run's map memory."""
    with (
        patch("overworld_map.service.get_map_memory", return_value=None),
        patch("overworld_map.service.get_map_entity_memories_for_map", return_value=[]),
        patch("overworld_map.service.get_warp_memories_for_map", return_value=[]),
        patch("overworld_map.service.get_map_boundary_memories_for_map", return_value=[]),
        patch("overworld_map.service.get_visited_maps", return_value=[]),
        patch("overworld_map.service.create_map_memory", return_value=None),
        patch("overworld_map.service.update_map_terrain", return_value=None),
        patch("overworld_map.service._discover_map_entities", return_value=None),
        patch("overworld_map.service.remember_warps", return_value=None),
    ):
        yield


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

        current_map = await _get_current_map(emulator)
        await solve_sokoban(
            iteration=0,
            emulator=emulator,
            current_map=current_map,
            rolling_memory=RollingMemory(),
        )

        game_state = await emulator.get_game_state()
        boulders = _get_boulders(game_state)
        assert len(boulders) == 1
        assert boulders == {Coords(row=13, col=17)}


@pytest.mark.integration
async def test_solve_remaining_puzzle_with_occupied_pressure_plate() -> None:
    """Solve the remaining hole without moving the completed plate or spare boulders."""
    plate_boulder_id = 7
    hole_boulder_id = 10
    save_file = Path(__file__).parent / "saves" / "sokoban_victory_road_3f.state"
    async with Emulator(save_state_path=save_file, mute_sound=True, headless=True) as emulator:
        await emulator._worker.execute(_suppress_random_encounters)
        game_state = await emulator.get_game_state()
        assert game_state.sprites[plate_boulder_id].coords == Coords(row=5, col=3)
        assert game_state.sprites[hole_boulder_id].coords == Coords(row=15, col=22)
        untouched_boulders = {
            entity_id: sprite.coords
            for entity_id, sprite in game_state.sprites.items()
            if sprite.label == SpriteLabel.BOULDER and entity_id != hole_boulder_id
        }
        current_map = await _get_current_map(emulator)
        current_map.terrain = [
            [str(tile) for tile in row] for row in game_state.get_ascii_map_terrain()
        ]
        await solve_sokoban(
            iteration=0,
            emulator=emulator,
            current_map=current_map,
            rolling_memory=RollingMemory(),
        )

        game_state = await emulator.get_game_state()
        assert {
            entity_id: sprite.coords
            for entity_id, sprite in game_state.sprites.items()
            if sprite.label == SpriteLabel.BOULDER
        } == untouched_boulders


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
        # Seafoam permits encounters on every indoor tile, and even turning can start one. Prevent
        # an unrelated wild battle from interrupting this deterministic Sokoban integration test.
        await emulator._worker.execute(_suppress_random_encounters)
        game_state = await emulator.get_game_state()
        assert game_state.player.coords == Coords(row=15, col=6)

        boulders = _get_boulders(game_state)
        assert len(boulders) == expected_num_boulders_before
        assert Coords(row=15, col=3) in boulders
        assert Coords(row=14, col=5) in boulders

        current_map = await _get_current_map(emulator)
        await solve_sokoban(
            iteration=0,
            emulator=emulator,
            current_map=current_map,
            rolling_memory=RollingMemory(),
        )

        game_state = await emulator.get_game_state()
        boulders = {
            sprite.coords
            for sprite in game_state.sprites.values()
            if sprite.label == SpriteLabel.BOULDER
        }
        assert len(boulders) == expected_num_boulders_after
        assert Coords(row=14, col=2) in boulders
        assert Coords(row=12, col=9) in boulders


def _suppress_random_encounters(pyboy: PyBoy) -> None:
    """Give the test enough encounter-free steps to finish both solutions."""
    pyboy.memory[_NO_RANDOM_BATTLE_STEPS_ADDRESS] = _MAX_BYTE


async def _get_current_map(emulator: Emulator) -> OverworldMap:
    """Prepare a map for the puzzle without loading or persisting map memory."""
    game_state = await emulator.get_game_state()
    overworld_map = await prepare_overworld_map(0, game_state)
    overworld_map.known_sprite_ids = set(game_state.sprites)
    return overworld_map


def _get_boulders(game_state: GameState) -> set[Coords]:
    """Get the boulders visible on the current screen."""
    return {
        s.coords
        for s in game_state.sprites.values()
        if s.label == SpriteLabel.BOULDER and s.is_rendered
    }
