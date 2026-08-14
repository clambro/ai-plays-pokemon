"""Integration tests for the application-facing emulator."""

import asyncio
from pathlib import Path

import pytest

from common.enums import Button
from emulator.control_events import ControlBoundary
from emulator.emulator import Emulator
from emulator.text_events import TextEventKind


@pytest.mark.integration
async def test_capture_and_restore_save_state() -> None:
    """Capture a save state on the owner thread and restore it in a new emulator."""
    save_file = Path(__file__).parent / "saves" / "mt_moon_poke_center.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        expected_state = await emulator.get_game_state()
        save_state = await emulator.get_emulator_save_state()

    async with Emulator(
        save_state=save_state,
        mute_sound=True,
        headless=True,
    ) as emulator:
        restored_state = await emulator.get_game_state()

    assert restored_state.map.id == expected_state.map.id
    assert restored_state.player.coords == expected_state.player.coords
    assert restored_state.party == expected_state.party
    assert restored_state.inventory == expected_state.inventory


@pytest.mark.integration
async def test_overworld_control_hands_dialog_to_text_consumer() -> None:
    """Stop at rendered text input without claiming the dialog events."""
    save_file = Path(__file__).parent / "saves" / "mt_moon_poke_center.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        emulator.drain_text_events()
        await asyncio.wait_for(emulator.press_overworld_button(Button.RIGHT), timeout=5)
        await asyncio.wait_for(emulator.press_overworld_button(Button.UP), timeout=5)
        result = await asyncio.wait_for(emulator.press_overworld_button(Button.A), timeout=5)

        game_state = await emulator.get_game_state()
        events = emulator.drain_text_events()
        remaining_events = emulator.drain_text_events()

    assert result.boundary == ControlBoundary.TEXT_INPUT_READY
    assert game_state.is_text_on_screen()
    assert any(event.kind == TextEventKind.INPUT_REQUIRED for event in events)
    assert remaining_events == ()
