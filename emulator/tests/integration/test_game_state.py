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
            "∙⌄⌄⌄⌄⌄⌄⌄⌄⌄",
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
    Test that the ASCII screen is correct for all the weird blocking corners in Mt Moon.

    Specifically making sure that the special tile exceptions in caverns are accounted for.
    """
    await _helper_test_expected_screen(
        state_filename="mt_moon_corners.state",
        expected_blockages={
            Coords(row=0, col=4): BlockedDirection.RIGHT,
            Coords(row=0, col=5): BlockedDirection.LEFT,
            Coords(row=1, col=4): BlockedDirection.RIGHT,
            Coords(row=1, col=5): BlockedDirection.LEFT,
            Coords(row=2, col=4): BlockedDirection.RIGHT,
            Coords(row=2, col=5): BlockedDirection.LEFT,
            Coords(row=0, col=8): BlockedDirection.RIGHT,
            Coords(row=0, col=9): BlockedDirection.LEFT,
            Coords(row=2, col=8): BlockedDirection.RIGHT,
            Coords(row=2, col=9): BlockedDirection.LEFT,
            Coords(row=3, col=8): BlockedDirection.RIGHT,
            Coords(row=3, col=9): BlockedDirection.LEFT,
            Coords(row=4, col=8): BlockedDirection.RIGHT,
            Coords(row=4, col=9): BlockedDirection.LEFT,
            Coords(row=6, col=8): BlockedDirection.RIGHT,
            Coords(row=6, col=9): BlockedDirection.LEFT,
            Coords(row=8, col=8): BlockedDirection.RIGHT,
            Coords(row=8, col=9): BlockedDirection.LEFT,
            Coords(row=2, col=0): BlockedDirection.UP,
            Coords(row=1, col=0): BlockedDirection.DOWN,
            Coords(row=2, col=1): BlockedDirection.UP,
            Coords(row=1, col=1): BlockedDirection.DOWN,
            Coords(row=2, col=2): BlockedDirection.UP,
            Coords(row=1, col=2): BlockedDirection.DOWN,
            Coords(row=8, col=2): BlockedDirection.UP,
            Coords(row=7, col=2): BlockedDirection.DOWN,
            Coords(row=8, col=3): BlockedDirection.UP,
            Coords(row=7, col=3): BlockedDirection.DOWN,
            Coords(row=8, col=6): BlockedDirection.UP,
            Coords(row=7, col=6): BlockedDirection.DOWN,
        },
        expected_screen=[
            "∙∙∙▉∙∙∙▉∙∙",
            "∙∙∙▉∙∙∙▉▉∙",
            "∙∙∙▉∙∙∙▉∙∙",
            "▉▉▉▉▉∙∙▉∙∙",
            "∙∙∙∙☻◈∙▉∙∙",
            "‼◆∙∙∙∙∙▉▉∙",
            "∙∙∙∙∙∙∙▉∙∙",
            "∙∙∙∙∙∙∙▉▉∙",
            "∙▉∙∙▉▉∙∙∙∙",
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
            "⌄⌄≋≋≋≋≋≋⌄∙",
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
    """Test that the ASCII screen is correct for the three ledges."""
    await _helper_test_expected_screen(
        state_filename="three_ledges.state",
        expected_blockages={},
        expected_screen=[
            "▉▉▉▉▉▉▉▉▉▉",
            "▉▉▉▉▉▉▉▉▉▉",
            "∙∙⌊∙∙∙∙⌋∙⌋",
            "∙∙⌊∙∙∙∙⌋∙⌋",
            "∙∙⌊∙☻∙∙⌋∙⌋",
            "∙∙⌄⌄⌄∙⌄⌋∙⌋",
            "∙∙∙∙∙∙∙∙∙⌋",
            "∙∙∙∙∙∙∙∙∙⌋",
            "∙∙∙∙∙∙∙∙∙⌋",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_rocket_spinners() -> None:
    """Test that the ASCII screen is correct for the Rocket Spinners."""
    await _helper_test_expected_screen(
        state_filename="rocket_spinners.state",
        expected_blockages={},
        expected_screen=[
            "▉∙⊙∙←∙∙∙←∙",
            "▉▉▉∙∙▉▉▉▉▉",
            "▉◆▉∙→∙∙∙⊙∙",
            "▉∙▉∙▉▉◆▉⇧▉",
            "▉∙∙∙☻▉▉▉∙▉",
            "▉▉▉▉∙→∙∙∙⇩",
            "▉∙∙∙→∙∙∙⇧∙",
            "▉∙▉▉⇧▉▉▉∙⊙",
            "▉∙∙∙∙▉▉▉▉▉",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_gym4_tree() -> None:
    """Test that the ASCII screen is correct for the cut trees in Gym 4."""
    await _helper_test_expected_screen(
        state_filename="gym4_tree.state",
        expected_blockages={},
        expected_screen=[
            "∙◆▉∙∙∙∙┬∙◆",
            "∙∙▉∙∙∙∙▉∙∙",
            "∙∙▉▉▉┬▉▉∙∙",
            "∙∙▉▉∙∙▉▉∙∙",
            "∙∙▉▉☻∙▉▉∙∙",
            "∙∙∙∙◈∙∙◆∙▉",
            "▉∙◆∙∙∙∙∙∙∙",
            "∙∙▉▉∙∙▉▉∙∙",
            "∙∙▉▉∙∙▉▉∙∙",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_seafoam_collisions() -> None:
    """Test that the ASCII screen is correct for the collisions in Seafoam Islands."""
    await _helper_test_expected_screen(
        state_filename="seafoam_collisions.state",
        expected_blockages={
            **{Coords(row=1, col=c): BlockedDirection.DOWN for c in range(2, 9)},
            **{Coords(row=2, col=c): BlockedDirection.UP for c in range(2, 9)},
        },
        expected_screen=[
            "≋≋≋≋≋≋≋≋≋▉",
            "≋≋≋≋≋≋≋≋≋▉",
            "≋▉∙∙∙∙∙∙∙∙",
            "≋▉∙∙∙∙⇆∙∙∙",
            "≋▉∙◈☻∙∙∙∙∙",
            "≋▉∙∙∙∙∙∙∙∙",
            "≋▉∙∙∙∙∙∙∙∙",
            "≋▉∙▉▉▉▉▉∙∙",
            "≋≋≋≋≋≋≋▉∙∙",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_seafoam_boulder_holes() -> None:
    """Test that the ASCII screen is correct for the boulder holes in Seafoam Islands."""
    await _helper_test_expected_screen(
        state_filename="seafoam_boulder_holes.state",
        expected_blockages={},
        expected_screen=[
            "▉▉∙∙∙∙∙∙∙∙",
            "▉▉∙∙∙∙∙∙∙∙",
            "▉▉∙∙∙∙∙∙∙∙",
            "▉▉∙∙∙∙∙∙▉▉",
            "▉▉∙∙☻◈⇆∙▉∙",
            "▉▉▉▉▉▉▉▉▉∙",
            "▉∙∙∙∙∙◆∙▉◆",
            "▉∙∙∙◆▉∙∙∙∙",
            "▉∙∙∙◌▉∙◌∙∙",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_gym8_spinners() -> None:
    """Test that the ASCII screen is correct for the spinners in Gym 8."""
    await _helper_test_expected_screen(
        state_filename="gym8_spinners.state",
        expected_blockages={},
        expected_screen=[
            "∙∙∙∙∙▉◆▉∙∙",
            "∙∙∙∙∙▉⇩▉∙∙",
            "∙◆∙∙∙▉∙▉⊙⇧",
            "▉▉▉▉◈∙⊙∙∙∙",
            "∙∙∙⊙☻∙∙∙∙∙",
            "∙∙∙⊙∙▉∙∙▉∙",
            "▉▉▉▉∙▉◆∙▉∙",
            "∙∙∙←∙∙∙∙∙∙",
            "∙∙∙←∙∙⇆⇆∙∙",
        ],
    )


@pytest.mark.integration
async def test_get_ascii_screen_victory_road_pressure_plate() -> None:
    """Test that the ASCII screen is correct for a pressure plate in Victory Road."""
    await _helper_test_expected_screen(
        state_filename="victory_road_plate.state",
        expected_blockages={},
        expected_screen=[
            "▉∙∙▉▉▉▉▉▉▉",
            "▉∙∙▉▉∙∙∙▉▉",
            "∙∙◆▉∙∙∙∙▉▉",
            "▉▉▉▉∙▉∙□▉▉",
            "∙∙∙◈☻∙∙▉▉▉",
            "▉▉∙∙∙∙∙▉▉▉",
            "▉▉∙∙▉▉▉▉▉▉",
            "▉▉▉▉▉▉▉▉▉▉",
            "▉▉▉▉▉▉▉▉▉▉",
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

    assert str(screen).split("\n") == expected_screen
    assert screen.blockages == expected_blockages
