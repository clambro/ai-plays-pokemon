"""Deterministic goal creation for the overworld agent."""

from copy import deepcopy

from memory.goals import Goal, Goals


class PrimaryGoalAlreadyExistsError(ValueError):
    """Raised when creation would add a second primary goal."""


def create_goal(
    *,
    goals: Goals,
    goal: str,
    is_primary: bool,
) -> Goals:
    """Append one new goal through the existing goal behavior.

    Args:
        goals: Current live goal collection.
        goal: Text of the new goal.
        is_primary: Whether the new goal is the primary goal.

    Returns:
        A revised goal collection containing the new goal.

    Raises:
        PrimaryGoalAlreadyExistsError: If you try to create a second primary goal.
    """
    if is_primary and any(existing_goal.is_primary for existing_goal in goals.goals):
        raise PrimaryGoalAlreadyExistsError(
            "A primary goal already exists. Update it instead, or delete it and create another.",
        )

    updated_goals = deepcopy(goals)
    updated_goals.append(Goal(goal=goal, is_primary=is_primary))
    return updated_goals
