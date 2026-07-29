"""Tests for the fight tool service."""

from pathlib import Path

import pytest

from agent.subflows.battle_handler.tools.fight.service import fight
from emulator.emulator import YellowLegacyEmulator
from memory.rolling_memory import RollingMemory


@pytest.mark.integration
async def test_use_move() -> None:
    """Test using the move with index 2 in battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
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

        rolling_memory = RollingMemory()
        await fight(
            rolling_memory=rolling_memory,
            emulator=emulator,
            reason="LEER will lower the opponent's defense.",
            move_slot=move_index,
        )
        await emulator.wait_for_animation_to_finish()

        game_state = await emulator.get_game_state()
        assert game_state.battle.player_pokemon is not None
        assert game_state.battle.player_pokemon.moves[move_index].pp == initial_pp - 1
        assert len(rolling_memory.raw_blocks) == 1
