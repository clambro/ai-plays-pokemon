"""Tests for the swap first Pokémon service."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from agent.subflows.overworld_handler.nodes.swap_first_pokemon.schemas import (
    SwapFirstPokemonResponse,
)
from agent.subflows.overworld_handler.nodes.swap_first_pokemon.service import (
    SwapFirstPokemonService,
)
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory


@pytest.mark.integration
async def test_switch_to_pokemon(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test switching the first Pokemon in the party with the one at position 3."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()
        party_index = 3
        assert len(game_state.party) >= party_index

        first_pokemon = game_state.party[0]
        index_pokemon = game_state.party[party_index]

        raw_memory = RawMemory()
        raw_memory.add_memory(
            iteration=0,
            content=(
                f"I need to put {index_pokemon.name} the {index_pokemon.species} in the first"
                f" position in my party."
            ),
        )

        service = SwapFirstPokemonService(
            iteration=0,
            raw_memory=raw_memory,
            emulator=emulator,
        )
        monkeypatch.setattr(
            service.llm_service,
            "get_llm_response_pydantic",
            AsyncMock(
                return_value=SwapFirstPokemonResponse(
                    thoughts="Move the requested Pokémon to the front.",
                    index=party_index,
                )
            ),
        )
        raw_memory = await service.swap_first_pokemon()
        await emulator.wait_for_animation_to_finish()

        game_state = await emulator.get_game_state()
        assert game_state.party[0] == index_pokemon
        assert game_state.party[party_index] == first_pokemon
        assert len(raw_memory.pieces) == 1
