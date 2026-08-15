"""Deterministic goal creation for the overworld agent."""

from copy import deepcopy

from memory.goals import MAX_GOALS, Goal, Goals


class GoalLimitReachedError(ValueError):
    """Raised when creation would exceed the goal limit."""


def create_goal(
    *,
    goals: Goals,
    goal: str,
    iteration: int,
) -> Goals:
    """Append one goal through the existing goal behavior.

    Args:
        goals: Current live goal collection.
        goal: Text of the new goal.
        iteration: Current application iteration.

    Returns:
        A revised goal collection containing the new goal.

    Raises:
        GoalLimitReachedError: If the goal limit has been reached.
    """
    if len(goals.goals) >= MAX_GOALS:
        raise GoalLimitReachedError(
            f"{MAX_GOALS} goals already exist. Update or delete one before creating another.",
        )

    updated_goals = deepcopy(goals)
    updated_goals.append(
        Goal(goal=goal, updated_at_iteration=iteration),
    )
    return updated_goals
