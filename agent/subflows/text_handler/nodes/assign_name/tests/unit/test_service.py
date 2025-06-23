from agent.subflows.text_handler.nodes.assign_name.service import AssignNameService
from common.enums import Button


def test_same_position_no_movement() -> None:
    """Test when cursor is already at the target letter position."""
    cursor_loc = 5  # cursor_row=0, cursor_col=0
    letter_loc = (0, 0)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert result == []


def test_simple_right_movement() -> None:
    """Test simple rightward movement within the same row."""
    cursor_loc = 5  # cursor_row=0, cursor_col=0
    letter_loc = (0, 1)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert result == [Button.RIGHT]


def test_simple_left_movement() -> None:
    """Test simple leftward movement within the same row."""
    cursor_loc = 7  # cursor_row=0, cursor_col=1
    letter_loc = (0, 0)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert result == [Button.LEFT]


def test_simple_down_movement() -> None:
    """Test simple downward movement to next row."""
    cursor_loc = 5  # cursor_row=0, cursor_col=0
    letter_loc = (1, 0)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert result == [Button.DOWN]


def test_simple_up_movement() -> None:
    """Test simple upward movement to previous row."""
    cursor_loc = 45  # cursor_row=1, cursor_col=0
    letter_loc = (0, 0)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert result == [Button.UP]


def test_diagonal_movement() -> None:
    """Test diagonal movement (both row and column change)."""
    cursor_loc = 5  # cursor_row=0, cursor_col=0
    letter_loc = (1, 1)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert set(result) == {Button.DOWN, Button.RIGHT}


def test_wrapping_right_to_left() -> None:
    """Test wrapping from right edge to left edge (shorter path)."""
    # cursor_row=0, cursor_col=8
    cursor_loc = 21
    letter_loc = (0, 0)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert result == [Button.RIGHT]


def test_wrapping_left_to_right() -> None:
    """Test wrapping from left edge to right edge (shorter path)."""
    cursor_loc = 5  # cursor_row=0, cursor_col=0
    letter_loc = (0, 8)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert result == [Button.LEFT]


def test_no_wrapping_when_not_shorter() -> None:
    """Test that wrapping doesn't occur when direct path is shorter."""
    cursor_loc = 5  # cursor_row=0, cursor_col=0
    letter_loc = (0, 4)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert result == [Button.RIGHT, Button.RIGHT, Button.RIGHT, Button.RIGHT]


def test_wrapping_threshold_edge_case() -> None:
    """Test the edge case at the wrapping threshold."""
    cursor_loc = 5  # cursor_row=0, cursor_col=0
    letter_loc = (0, 5)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert result == [Button.LEFT, Button.LEFT, Button.LEFT, Button.LEFT]


def test_cross_row_wrapping() -> None:
    """Test wrapping combined with row movement."""
    cursor_loc = 21  # cursor_row=0, cursor_col=8
    letter_loc = (1, 0)

    result = AssignNameService._get_dir_buttons(letter_loc, cursor_loc)

    assert set(result) == {Button.DOWN, Button.RIGHT}
