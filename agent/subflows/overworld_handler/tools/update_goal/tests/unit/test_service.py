"""Tests for deterministic single-goal updates."""

import pytest

from agent.subflows.overworld_handler.tools.update_goal.service import (
    GoalNotFoundError,
    update_goal,
)
from memory.goals import Goal, GoalPriority, Goals


@pytest.mark.unit
def test_update_goal_replaces_one_goal_without_mutating_input() -> None:
    """Replace one indexed goal and preserve the original collection."""
    original = Goal(goal="Reach Pewter City.", priority=GoalPriority.SECONDARY)
    goals = Goals(goals=[original])

    updated = update_goal(
        goals=goals,
        index=0,
        goal="Enter the Pewter City Gym.",
        priority=GoalPriority.SECONDARY,
    )

    assert goals.goals == [original]
    assert updated.goals == [
        Goal(goal="Enter the Pewter City Gym.", priority=GoalPriority.SECONDARY)
    ]


@pytest.mark.unit
def test_update_goal_rejects_an_unknown_index() -> None:
    """Reject an index that does not identify a current goal."""
    goals = Goals()

    with pytest.raises(GoalNotFoundError, match="does not exist"):
        update_goal(
            goals=goals,
            index=0,
            goal="Reach Pewter City.",
            priority=GoalPriority.SECONDARY,
        )
