"""Tests for the assign name service."""

import pytest

from agent.text.tools.assign_name.service import _get_dir_buttons
from common.enums import Button


@pytest.mark.unit
@pytest.mark.parametrize(
    ("cursor_loc", "letter_loc", "expected"),
    [
        pytest.param(5, (0, 0), [], id="same-position"),
        pytest.param(5, (0, 1), [Button.RIGHT], id="right"),
        pytest.param(7, (0, 0), [Button.LEFT], id="left"),
        pytest.param(5, (1, 0), [Button.DOWN], id="down"),
        pytest.param(45, (0, 0), [Button.UP], id="up"),
        pytest.param(21, (0, 0), [Button.RIGHT], id="wrap-right-to-left"),
        pytest.param(5, (0, 8), [Button.LEFT], id="wrap-left-to-right"),
        pytest.param(5, (0, 4), [Button.RIGHT] * 4, id="direct-path-shorter"),
        pytest.param(5, (0, 5), [Button.LEFT] * 4, id="wrapping-threshold"),
    ],
)
def test_direction_buttons(
    cursor_loc: int, letter_loc: tuple[int, int], expected: list[Button]
) -> None:
    """Move to a letter using the shorter route, including horizontal wrapping."""
    assert _get_dir_buttons(letter_loc, cursor_loc) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("cursor_loc", "letter_loc"),
    [
        pytest.param(5, (1, 1), id="diagonal"),
        pytest.param(21, (1, 0), id="cross-row-wrapping"),
    ],
)
def test_diagonal_direction_buttons(cursor_loc: int, letter_loc: tuple[int, int]) -> None:
    """Move across rows and columns without prescribing which axis moves first."""
    assert set(_get_dir_buttons(letter_loc, cursor_loc)) == {Button.DOWN, Button.RIGHT}
