"""Tests for the run tool service."""

from pathlib import Path

import pytest

from agent.subflows.battle_handler.nodes.run_tool.service import run_away
from emulator.emulator import YellowLegacyEmulator
from memory.rolling_memory import RollingMemory


@pytest.mark.integration
async def test_run_away_from_battle() -> None:
    """Test running away from battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()

        # Verify that the initial state is as expected.
        assert game_state.battle.is_in_battle

        rolling_memory = await run_away(
            rolling_memory=RollingMemory(),
            emulator=emulator,
        )
        await emulator.wait_for_animation_to_finish()

        game_state = await emulator.get_game_state()
        assert "No! There's no" in game_state.screen.text  # Trainer battle run text.
        assert len(rolling_memory.raw_blocks) == 1
