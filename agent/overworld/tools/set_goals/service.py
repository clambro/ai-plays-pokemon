"""Complete goal-list replacement for the overworld agent."""

from memory.goals import MAX_GOALS, MIN_GOALS, Goal


class GoalChangeError(ValueError):
    """Raised when a replacement goal list is invalid."""


def set_goals(
    *,
    goals: list[str],
    iteration: int,
) -> list[Goal]:
    """Build a complete goal list, marking every entry as reviewed.

    Args:
        goals: Complete replacement list, including any unchanged goals.
        iteration: Current application iteration.

    Returns:
        A new goal list with trimmed text and the current review iteration.

    Raises:
        GoalChangeError: The list is outside the allowed size or contains blank goals.
    """
    if not MIN_GOALS <= len(goals) <= MAX_GOALS:
        raise GoalChangeError(f"Keep between {MIN_GOALS} and {MAX_GOALS} goals.")
    goal_texts = [goal.strip() for goal in goals]
    if not all(goal_texts):
        raise GoalChangeError("Goals cannot be blank.")
    return [Goal(goal=goal, updated_at_iteration=iteration) for goal in goal_texts]
