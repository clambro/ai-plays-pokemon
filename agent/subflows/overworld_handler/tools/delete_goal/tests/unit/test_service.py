"""Tests for deterministic single-goal deletion."""

import pytest

from agent.subflows.overworld_handler.tools.delete_goal.service import (
    GoalNotFoundError,
    delete_goal,
)
from memory.goals import Goal, GoalPriority, Goals


@pytest.mark.unit
def test_delete_goal_removes_one_goal_without_mutating_input() -> None:
    """Delete one indexed goal and return the deleted value."""
    primary = Goal(goal="Defeat Brock.", priority=GoalPriority.PRIMARY)
    completed = Goal(goal="Reach Pewter City.", priority=GoalPriority.SECONDARY)
    goals = Goals(goals=[primary, completed])

    updated, deleted = delete_goal(goals=goals, index=1)

    assert goals.goals == [primary, completed]
    assert updated.goals == [primary]
    assert deleted == completed


@pytest.mark.unit
def test_delete_goal_rejects_an_unknown_index() -> None:
    """Reject an index that does not identify a current goal."""
    goals = Goals()

    with pytest.raises(GoalNotFoundError, match="does not exist"):
        delete_goal(goals=goals, index=0)
