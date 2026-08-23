"""Integration tests for the application-facing emulator."""

import asyncio
from pathlib import Path

import pytest

from common.enums import Button, MapEntityType
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
        starting_coords = (await emulator.get_game_state()).player.coords
        await asyncio.wait_for(emulator.press_overworld_button(Button.RIGHT), timeout=5)
        if (await emulator.get_game_state()).player.coords == starting_coords:
            await asyncio.wait_for(emulator.press_overworld_button(Button.RIGHT), timeout=5)
        await asyncio.wait_for(emulator.press_overworld_button(Button.UP), timeout=5)
        result = await asyncio.wait_for(emulator.press_overworld_button(Button.A), timeout=5)

        game_state = await emulator.get_game_state()
        events = emulator.drain_text_events()
        remaining_events = emulator.drain_text_events()

    assert result.boundary == ControlBoundary.TEXT_INPUT_READY
    assert game_state.is_text_on_screen()
    assert any(event.kind == TextEventKind.INPUT_REQUIRED for event in events)
    interaction_starts = [
        event for event in events if event.kind == TextEventKind.MAP_ENTITY_INTERACTION_STARTED
    ]
    assert len(interaction_starts) == 1
    target = interaction_starts[0].interaction_target
    assert target is not None
    assert target.map_id == game_state.map.id
    assert target.entity_type == MapEntityType.SPRITE
    assert target.entity_id in game_state.sprites
    assert remaining_events == ()


@pytest.mark.integration
async def test_sign_dialog_is_attributed_to_its_map_sign() -> None:
    """Identify the exact map-local sign selected by the ROM's sign loop."""
    expected_sign_id = 2
    save_file = Path(__file__).parent / "saves" / "viridian_flowers.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        emulator.drain_text_events()
        for button in (
            Button.LEFT,
            Button.LEFT,
            Button.DOWN,
            Button.DOWN,
            Button.LEFT,
            Button.A,
        ):
            result = await asyncio.wait_for(emulator.press_overworld_button(button), timeout=5)

        game_state = await emulator.get_game_state()
        events = emulator.drain_text_events()

    assert result.boundary == ControlBoundary.TEXT_INPUT_READY
    interaction_starts = [
        event for event in events if event.kind == TextEventKind.MAP_ENTITY_INTERACTION_STARTED
    ]
    assert len(interaction_starts) == 1
    target = interaction_starts[0].interaction_target
    assert target is not None
    assert target.map_id == game_state.map.id
    assert target.entity_type == MapEntityType.SIGN
    assert target.entity_id == expected_sign_id
    assert target.entity_id in game_state.signs


@pytest.mark.integration
async def test_static_object_dialog_is_attributed_to_its_map_object() -> None:
    """Identify the exact supported object selected by the ROM's lookup."""
    save_file = Path(__file__).parent / "saves" / "mt_moon_poke_center.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        emulator.drain_text_events()
        for button in (Button.RIGHT,) * 12 + (Button.UP, Button.A):
            result = await asyncio.wait_for(emulator.press_overworld_button(button), timeout=5)

        game_state = await emulator.get_game_state()
        events = emulator.drain_text_events()

    assert result.boundary == ControlBoundary.TEXT_INPUT_READY
    interaction_starts = [
        event for event in events if event.kind == TextEventKind.MAP_ENTITY_INTERACTION_STARTED
    ]
    assert len(interaction_starts) == 1
    target = interaction_starts[0].interaction_target
    assert target is not None
    assert target.map_id == game_state.map.id
    assert target.entity_type == MapEntityType.OBJECT
    assert target.entity_id == 1
    assert target.entity_id in game_state.objects
