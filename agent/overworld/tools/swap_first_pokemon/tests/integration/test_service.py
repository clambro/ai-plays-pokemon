"""Tests for the swap first Pokémon service."""

from pathlib import Path

import pytest

from agent.overworld.tools.swap_first_pokemon.service import (
    SwapFirstPokemonService,
)
from emulator.emulator import Emulator
from memory.rolling_memory.schemas import RollingMemory


@pytest.mark.integration
async def test_switch_to_pokemon() -> None:
    """Test switching the first Pokemon in the party with the one at position 3."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        party_index = 3
        assert len(game_state.party) >= party_index

        first_pokemon = game_state.party[0]
        index_pokemon = game_state.party[party_index]

        rolling_memory = RollingMemory()
        rolling_memory.add_memory(
            content=(
                f"I need to put {index_pokemon.name} the {index_pokemon.species} in the first"
                f" position in my party."
            ),
        )

        service = SwapFirstPokemonService(
            rolling_memory=rolling_memory,
            emulator=emulator,
        )
        await service.swap_first_pokemon(party_index)
        await emulator.wait_for_animation_to_finish()

        game_state = await emulator.get_game_state()
        assert game_state.party[0] == index_pokemon
        assert game_state.party[party_index] == first_pokemon
        assert len(rolling_memory.raw_blocks) == 1
