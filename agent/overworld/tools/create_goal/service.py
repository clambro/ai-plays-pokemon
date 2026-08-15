"""Deterministic goal creation for the overworld agent."""

from copy import deepcopy

from memory.goals import Goal, Goals

_MAX_SECONDARY_GOALS = 3


class SecondaryGoalLimitReachedError(ValueError):
    """Raised when creation would add more than three secondary goals."""


class PrimaryGoalAlreadyExistsError(ValueError):
    """Raised when creation would add a second primary goal."""


def create_goal(
    *,
    goals: Goals,
    goal: str,
    is_primary: bool,
    iteration: int,
) -> Goals:
    """Append one new goal through the existing goal behavior.

    Args:
        goals: Current live goal collection.
        goal: Text of the new goal.
        is_primary: Whether the new goal is the primary goal.
        iteration: Current application iteration.

    Returns:
        A revised goal collection containing the new goal.

    Raises:
        SecondaryGoalLimitReachedError: If three secondary goals already exist.
        PrimaryGoalAlreadyExistsError: If you try to create a second primary goal.
    """
    if is_primary and any(existing_goal.is_primary for existing_goal in goals.goals):
        raise PrimaryGoalAlreadyExistsError(
            "A primary goal already exists. Update it instead, or delete it and create another.",
        )
    if (
        not is_primary
        and sum(not existing_goal.is_primary for existing_goal in goals.goals)
        >= _MAX_SECONDARY_GOALS
    ):
        raise SecondaryGoalLimitReachedError(
            "Three secondary goals already exist. Update or delete one before creating another.",
        )

    updated_goals = deepcopy(goals)
    updated_goals.append(
        Goal(
            goal=goal,
            is_primary=is_primary,
            updated_at_iteration=iteration,
        ),
    )
    return updated_goals
