from pathlib import Path

import pytest

from agent.subflows.battle_handler.nodes.run_tool.service import RunToolService
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory


@pytest.mark.integration
async def test_run_away_from_battle() -> None:
    """Test running away from battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = emulator.get_game_state()

        # Verify that the initial state is as expected.
        assert game_state.battle.is_in_battle

        service = RunToolService(
            iteration=0,
            raw_memory=RawMemory(),
            emulator=emulator,
        )
        raw_memory = await service.run_away()
        await emulator.wait_for_animation_to_finish()

        game_state = emulator.get_game_state()
        assert "No! There's no" in game_state.screen.text  # Trainer battle run text.
        assert len(raw_memory.pieces) == 1
