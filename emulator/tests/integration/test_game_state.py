"""
Tests for the game state.

For the ASCII screen tests, it's a bit of an antipattern to use strings instead of the enum values
because if we ever need to change the characters used, we'll have to update the tests, but this is
far more readable.
"""

from pathlib import Path

import numpy as np
import pytest

from emulator.emulator import YellowLegacyEmulator


@pytest.mark.integration
async def test_get_ascii_screen_viridian_flowers() -> None:
    """Test that the ASCII screen is correct for Viridian City near the flowers."""
    save_file = Path(__file__).parent / "saves" / "viridian_flowers.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = emulator.get_game_state()

    screen = game_state.get_ascii_screen()

    assert np.sum(screen.blockages) == 0
    assert str(screen).split("\n") == [
        "∙∙∙▉▉▉▉∙∙∙",
        "∙∙∙▉⇆‼▉∙∙∙",
        "∙∙∙∙∙∙∙∙∙∙",
        "∙⍖⍖⍖⍖⍖⍖⍖⍖⍖",
        "∙∙∙◈☻∙∙∙∙∙",
        "∙∙‼∙∙∙∙∙∙∙",
        "∙∙∙∙∙∙∙∙∙∙",
        "▉∙∙▉▉▉▉▉▉▉",
        "▉∙∙▉∙∙∙∙∙▉",
    ]
