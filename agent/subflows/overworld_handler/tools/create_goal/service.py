"""Deterministic goal creation for the overworld agent."""

from copy import deepcopy

from memory.goals import Goal, GoalPriority, Goals


def create_goal(
    *,
    goals: Goals,
    goal: str,
    priority: GoalPriority,
) -> Goals:
    """Append one new goal through the existing goal behavior.

    Args:
        goals: Current live goal collection.
        goal: Text of the new goal.
        priority: Priority assigned to the new goal.

    Returns:
        A revised goal collection containing the new goal.
    """
    updated_goals = deepcopy(goals)
    updated_goals.append(Goal(goal=goal, priority=priority))
    return updated_goals
