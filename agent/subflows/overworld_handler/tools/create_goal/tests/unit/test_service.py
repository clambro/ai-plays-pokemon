"""Tests for deterministic goal creation."""

import pytest

from agent.subflows.overworld_handler.tools.create_goal.service import create_goal
from memory.goals import Goal, GoalPriority, Goals


@pytest.mark.unit
def test_create_goal_appends_and_sorts_without_mutating_input() -> None:
    """Create one goal through the existing goal collection behavior."""
    tertiary = Goal(goal="Train Pikachu.", priority=GoalPriority.TERTIARY)
    goals = Goals(goals=[tertiary])

    updated = create_goal(
        goals=goals,
        goal="Defeat Brock and earn the BOULDERBADGE.",
        priority=GoalPriority.PRIMARY,
    )

    assert goals.goals == [tertiary]
    assert [goal.priority for goal in updated.goals] == [
        GoalPriority.PRIMARY,
        GoalPriority.TERTIARY,
    ]
