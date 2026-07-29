"""Tests for the run tool service."""

from pathlib import Path

import pytest

from agent.subflows.battle_handler.tools.errors import BattleActionUnavailableError
from agent.subflows.battle_handler.tools.run.service import run
from emulator.emulator import YellowLegacyEmulator
from memory.rolling_memory import RollingMemory


@pytest.mark.integration
async def test_cannot_run_from_trainer_battle() -> None:
    """Test rejecting a run attempt during a trainer battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()

        # Verify that the initial state is as expected.
        assert game_state.battle.is_in_battle

        rolling_memory = RollingMemory()
        with pytest.raises(BattleActionUnavailableError, match="wild battle"):
            await run(
                rolling_memory=rolling_memory,
                emulator=emulator,
            )
        assert not rolling_memory.raw_blocks
