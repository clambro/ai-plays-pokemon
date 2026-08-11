"""Tests for the switch Pokémon tool service."""

from pathlib import Path

import pytest

from agent.battle.tools.switch_pokemon.service import switch_pokemon
from emulator.emulator import Emulator


@pytest.mark.integration
async def test_switch_to_pokemon() -> None:
    """Test switching to Pokemon at position 1 in battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        party_index = 1

        # Verify that the initial state is as expected.
        assert game_state.battle.is_in_battle
        assert game_state.battle.player_pokemon is not None
        assert len(game_state.party) >= party_index

        await switch_pokemon(
            emulator=emulator,
            party_slot=party_index,
        )
        await emulator.wait_for_animation_to_finish()

        game_state = await emulator.get_game_state()
        assert game_state.battle.player_pokemon == game_state.party[party_index]
