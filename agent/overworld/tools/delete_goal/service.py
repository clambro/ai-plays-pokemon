"""Deterministic deletion of one overworld goal."""

from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory.goals import Goal, Goals


class GoalNotFoundError(ValueError):
    """Raised when a deletion refers to a goal index that does not exist."""


def delete_goal(*, goals: Goals, index: int) -> tuple[Goals, Goal]:
    """Delete one existing goal through the existing goal behavior.

    Args:
        goals: Current live goal collection.
        index: Zero-based index of the goal to delete.

    Returns:
        The revised goal collection and the goal that was deleted.

    Raises:
        GoalNotFoundError: The index does not identify a current goal.
    """
    if not 0 <= index < len(goals.goals):
        raise GoalNotFoundError(
            f"Goal index {index} does not exist; no goal was deleted.",
        )

    updated_goals = deepcopy(goals)
    deleted_goal = updated_goals.goals[index]
    updated_goals.remove(index)
    return updated_goals, deleted_goal
