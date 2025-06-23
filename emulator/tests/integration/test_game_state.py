"""
Tests for the game state.

For the ASCII screen tests, it's a bit of an antipattern to use strings instead of the enum values
because if we ever need to change the characters used, we'll have to update the tests, but this is
far more readable.
"""

from pathlib import Path

import pytest

from common.enums import BlockedDirection
from common.schemas import Coords
from emulator.emulator import YellowLegacyEmulator


@pytest.mark.integration
async def test_get_ascii_screen_viridian_flowers() -> None:
    """
    Test that the ASCII screen is correct for Viridian City near the flowers.

    Specifically making sure that the flowers don't break the free tile rendering.
    """
    await _helper_test_expected_screen(
        state_filename="viridian_flowers.state",
        expected_blockages={},
        expected_screen=[
            "∙∙∙▉▉▉▉∙∙∙",
            "∙∙∙▉⇆‼▉∙∙∙",
            "∙∙∙∙∙∙∙∙∙∙",
            "∙⍖⍖⍖⍖⍖⍖⍖⍖⍖",
            "∙∙∙◈☻∙∙∙∙∙",
            "∙∙‼∙∙∙∙∙∙∙",
            "∙∙∙∙∙∙∙∙∙∙",
            "▉∙∙▉▉▉▉▉▉▉",
            "▉∙∙▉∙∙∙∙∙▉",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_mt_moon_corners() -> None:
    """
    Test that the ASCII screen is correct for Mt. Moon near all the weird corner edge cases.

    Specifically making sure that the special tile exceptions in caverns are accounted for.
    """
    await _helper_test_expected_screen(
        state_filename="mt_moon_corners.state",
        expected_blockages={},
        expected_screen=[
            "∙∙∙▉▉∙∙▉▉∙",
            "∙∙∙▉▉∙∙▉▉∙",
            "▉▉▉▉▉∙∙▉▉∙",
            "▉▉▉▉▉∙∙▉▉∙",
            "∙∙∙∙☻◈∙▉▉∙",
            "‼◆∙∙∙∙∙▉▉∙",
            "∙∙∙∙∙∙∙▉▉∙",
            "∙∙∙∙∙∙∙▉▉∙",
            "∙▉▉▉▉▉▉▉▉∙",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_mt_moon_poke_center() -> None:
    """
    Test that the ASCII screen is correct for Mt. Moon Pokémon Center.

    Specifically making sure that Pokemon center floor tiles are rendered as free tiles.
    """
    await _helper_test_expected_screen(
        state_filename="mt_moon_poke_center.state",
        expected_blockages={},
        expected_screen=[
            "▉▉▉▉▉▉▉▉▉▉",
            "▉▉▉▉◆◆▉▉▉∙",
            "▉▉▉▉▉▉▉▉◆▉",
            "▉▉∙∙∙◆∙∙◆∙",
            "▉▉∙∙☻∙∙∙∙∙",
            "▉▉∙∙◈∙∙∙∙∙",
            "▉▉▉∙∙∙∙▉▉∙",
            "▉▉▉∙⇆⇆∙▉▉∙",
            "▉▉▉▉▉▉▉▉▉▉",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_viridian_water() -> None:
    """
    Test that the ASCII screen is correct for Viridian City near the water.

    Specifically making sure that the boundaries around water are rendered correctly, as well as
    the cut tree.
    """
    await _helper_test_expected_screen(
        state_filename="viridian_water.state",
        expected_blockages={},
        expected_screen=[
            "∙∙∙∙∙∙∙∙∙∙",
            "∙∙∙∙∙∙∙◆∙∙",
            "▉▉∙∙∙∙∙∙∙∙",
            "∙∙┬∙∙∙∙∙∙∙",
            "◆∙▉▉☻◈∙∙∙∙",
            "∙∙≋≋≋≋≋≋∙∙",
            "∙∙≋≋≋≋≋≋∙∙",
            "∙∙≋≋≋≋≋≋∙∙",
            "⍖⍖≋≋≋≋≋≋⍖∙",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_viridian_forest() -> None:
    """
    Test that the ASCII screen is correct for Viridian Forest.

    Checking the unique tilemap used here.
    """
    await _helper_test_expected_screen(
        state_filename="viridian_forest.state",
        expected_blockages={},
        expected_screen=[
            "❀∙∙❀▉▉▉▉▉▉",
            "❀∙∙❀▉▉▉▉▉▉",
            "❀∙∙❀❀❀❀❀❀‼",
            "❀▉▉❀❀❀❀❀❀❀",
            "∙▉▉∙☻∙∙∙∙∙",
            "∙◆∙∙◈∙∙∙∙∙",
            "∙∙∙∙▉▉▉▉▉▉",
            "∙∙∙‼▉▉▉▉▉▉",
            "∙∙∙∙▉▉▉▉▉▉",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_three_ledges() -> None:
    """
    Test that the ASCII screen is correct for the three ledges.

    Checking the unique tilemap used here.
    """
    await _helper_test_expected_screen(
        state_filename="three_ledges.state",
        expected_blockages={},
        expected_screen=[
            "▉▉▉▉▉▉▉▉▉▉",
            "▉▉▉▉▉▉▉▉▉▉",
            "∙∙⍅∙∙∙∙⍆∙⍆",
            "∙∙⍅∙∙∙∙⍆∙⍆",
            "∙∙⍅∙☻∙∙⍆∙⍆",
            "∙∙⍖⍖⍖∙⍖⍆∙⍆",
            "∙∙∙∙∙∙∙∙∙⍆",
            "∙∙∙∙∙∙∙∙∙⍆",
            "∙∙∙∙∙∙∙∙∙⍆",
        ],
    )


@pytest.mark.integration
async def _helper_test_expected_screen(
    state_filename: str,
    expected_blockages: dict[Coords, BlockedDirection],
    expected_screen: list[str],
) -> None:
    """
    Helper function to test the ASCII screen for a given state file.

    :param state_filename: The name of the state file to load.
    :param expected_blockages: The expected blockages in the screen.
    :param expected_screen: The expected screen as a list of strings.
    """
    save_file = Path(__file__).parent / "saves" / state_filename
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = emulator.get_game_state()

    screen = game_state.get_ascii_screen()

    assert screen.blockages == expected_blockages
    assert str(screen).split("\n") == expected_screen
