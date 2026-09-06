"""Mutable goal memory for gameplay agents."""

from dataclasses import dataclass

MIN_GOALS = 1
MAX_GOALS = 4


@dataclass(slots=True, kw_only=True)
class Goal:
    """A goal and the iteration when it was last set or reviewed."""

    goal: str
    updated_at_iteration: int
