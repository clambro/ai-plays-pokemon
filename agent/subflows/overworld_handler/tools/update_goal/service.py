"""Deterministic updates to one overworld goal."""

from copy import deepcopy

from memory.goals import Goal, GoalPriority, Goals


class GoalNotFoundError(ValueError):
    """Raised when an update refers to a goal index that does not exist."""


def update_goal(
    *,
    goals: Goals,
    index: int,
    goal: str,
    priority: GoalPriority,
) -> Goals:
    """Replace one existing goal through the existing goal behavior.

    Args:
        goals: Current live goal collection.
        index: Zero-based index of the goal to replace.
        goal: Complete revised goal text.
        priority: Priority assigned to the revised goal.

    Returns:
        A revised goal collection containing the replacement.

    Raises:
        GoalNotFoundError: The index does not identify a current goal.
    """
    if not 0 <= index < len(goals.goals):
        raise GoalNotFoundError(
            f"Goal index {index} does not exist; no goal was updated.",
        )

    updated_goals = deepcopy(goals)
    updated_goals.remove(index)
    updated_goals.append(Goal(goal=goal, priority=priority))
    return updated_goals
