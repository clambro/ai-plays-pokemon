"""Integration tests for the application-facing emulator."""

from pathlib import Path

import pytest

from emulator.emulator import YellowLegacyEmulator


@pytest.mark.integration
async def test_capture_and_restore_save_state() -> None:
    """Capture a save state on the owner thread and restore it in a new emulator."""
    save_file = Path(__file__).parent / "saves" / "mt_moon_poke_center.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        expected_state = await emulator.get_game_state()
        save_state = await emulator.get_emulator_save_state()

    async with YellowLegacyEmulator(
        save_state=save_state,
        mute_sound=True,
        headless=True,
    ) as emulator:
        restored_state = await emulator.get_game_state()

    assert restored_state.map.id == expected_state.map.id
    assert restored_state.player.coords == expected_state.player.coords
    assert restored_state.party == expected_state.party
    assert restored_state.inventory == expected_state.inventory
