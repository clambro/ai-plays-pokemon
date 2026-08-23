"""Deterministic indexed goal mutation for the overworld agent."""

from copy import deepcopy

from memory.goals import MAX_GOALS, Goal, Goals


class GoalChangeError(ValueError):
    """Raised when an indexed goal change is invalid."""


def set_goal(
    *,
    goals: Goals,
    index: int,
    goal: str | None,
    iteration: int,
) -> Goals:
    """Set or clear one goal while preserving a compact ordered list.

    Args:
        goals: Current live goal collection.
        index: Existing goal index, or the next index when appending.
        goal: Replacement goal text, or ``None`` to delete an existing goal.
        iteration: Current application iteration.

    Returns:
        The revised goal collection.

    Raises:
        GoalChangeError: The requested change is empty, out of range, or would exceed the limit.
    """
    updated_goals = deepcopy(goals)
    goal_count = len(updated_goals.goals)

    if index < 0:
        raise GoalChangeError("A goal index cannot be negative.")

    if goal is None:
        if not 0 <= index < goal_count:
            raise GoalChangeError(f"Goal index {index} does not exist; no goal was removed.")
        updated_goals.remove(index)
        return updated_goals

    goal = goal.strip()
    if not goal:
        raise GoalChangeError("A goal cannot be empty. Use null to remove an existing goal.")
    if index < goal_count:
        updated_goals.goals[index] = Goal(
            goal=goal,
            updated_at_iteration=iteration,
        )
        return updated_goals
    if index == goal_count and goal_count < MAX_GOALS:
        updated_goals.append(
            Goal(
                goal=goal,
                updated_at_iteration=iteration,
            ),
        )
        return updated_goals
    if goal_count >= MAX_GOALS:
        raise GoalChangeError(
            f"The goal list already contains the maximum of {MAX_GOALS} goals."
            " Replace or remove an existing goal.",
        )
    raise GoalChangeError(
        f"Goal index {index} would leave a gap. Use index {goal_count} to append the next goal.",
    )
