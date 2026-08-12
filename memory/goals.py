"""Mutable goal memory for gameplay agents."""

from dataclasses import dataclass, field


@dataclass(slots=True, kw_only=True)
class Goal:
    """A goal for the agent."""

    goal: str
    is_primary: bool


@dataclass(slots=True, kw_only=True)
class Goals:
    """The goals for the agent."""

    goals: list[Goal] = field(default_factory=list)

    def append(self, *goals: Goal) -> None:
        """Append new goals to the list."""
        for goal in goals:
            goal.goal = goal.goal.strip()
            self.goals.append(goal)
        self.goals = sorted(self.goals, key=lambda g: not g.is_primary)

    def remove(self, *indices: int) -> None:
        """Remove goals from the list."""
        for index in sorted(indices, reverse=True):  # Last-to-first to avoid index shifting.
            del self.goals[index]
