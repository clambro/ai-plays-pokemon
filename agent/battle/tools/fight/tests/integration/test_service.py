"""Tests for the fight tool service."""

from pathlib import Path

import pytest

from agent.battle.tools.fight.service import fight
from emulator.control_events import ControlBoundary
from emulator.emulator import Emulator


@pytest.mark.integration
async def test_use_move() -> None:
    """Test using the move with index 2 in battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        move_index = 2

        # Verify that the initial state is as expected.
        assert game_state.battle.is_in_battle
        assert game_state.battle.player_pokemon is not None
        assert len(game_state.battle.player_pokemon.moves) >= move_index

        initial_pp = game_state.battle.player_pokemon.moves[move_index].pp

        await fight(
            emulator=emulator,
            move_slot=move_index,
        )
        dialog = await emulator.advance_battle_dialog()

        game_state, boundary = await emulator.get_game_state_with_control_boundary()
        assert dialog
        assert boundary == ControlBoundary.MENU_READY
        assert game_state.battle.player_pokemon is not None
        assert game_state.battle.player_pokemon.moves[move_index].pp == initial_pp - 1
