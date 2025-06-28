from pathlib import Path

import pytest

from agent.subflows.battle_handler.nodes.fight_tool.service import FightToolService
from agent.subflows.battle_handler.schemas import FightToolArgs
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory


@pytest.mark.integration
async def test_use_move() -> None:
    """Test using the move with index 2 in battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = emulator.get_game_state()
        move_index = 2

        # Verify that the initial state is as expected.
        assert game_state.battle.is_in_battle
        assert game_state.battle.player_pokemon is not None
        assert len(game_state.battle.player_pokemon.moves) >= move_index

        initial_pp = game_state.battle.player_pokemon.moves[move_index].pp

        service = FightToolService(
            iteration=0,
            raw_memory=RawMemory(),
            tool_args=FightToolArgs(move_index=move_index, move_name="LEER"),
            emulator=emulator,
        )
        raw_memory = await service.fight()
        await emulator.wait_for_animation_to_finish()

        game_state = emulator.get_game_state()
        assert game_state.battle.player_pokemon is not None
        assert game_state.battle.player_pokemon.moves[move_index].pp == initial_pp - 1
        assert len(raw_memory.pieces) == 1
