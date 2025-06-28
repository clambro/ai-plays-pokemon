from pathlib import Path

import pytest

from agent.subflows.battle_handler.nodes.switch_pokemon_tool.service import SwitchPokemonToolService
from agent.subflows.battle_handler.schemas import SwitchPokemonToolArgs
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory


@pytest.mark.integration
async def test_switch_to_pokemon() -> None:
    """Test switching to Pokemon at position 1 in battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = emulator.get_game_state()
        party_index = 1

        # Verify that the initial state is as expected.
        assert game_state.battle.is_in_battle
        assert game_state.battle.player_pokemon is not None
        assert len(game_state.party) >= party_index

        service = SwitchPokemonToolService(
            iteration=0,
            raw_memory=RawMemory(),
            tool_args=SwitchPokemonToolArgs(
                party_index=party_index,
                name="Test Pokemon",
                species="Test Species",
            ),
            emulator=emulator,
        )
        raw_memory = await service.switch_pokemon()
        await emulator.wait_for_animation_to_finish()

        game_state = emulator.get_game_state()
        assert game_state.battle.player_pokemon == game_state.party[party_index]
        assert len(raw_memory.pieces) == 1
