from loguru import logger
from pydantic import BaseModel, Field


class Goals(BaseModel):
    """The goals for the agent."""

    goals: list[str] = Field(default_factory=list)

    def __str__(self) -> str:
        """Return a string representation of the goals."""
        out = (
            "Here are the goals that you have set for yourself. Your ultimate goal is, of course,"
            " to collect all eight badges and become the Elite Four Champion, but these goals here"
            " are the next steps on your journey to that goal."
        )
        out += "\n<goals>\n"
        if self.goals:
            out += "\n".join(f"[{i}] {g}" for i, g in enumerate(self.goals))
        else:
            out += "You have not set any goals yet."
        out += "\n</goals>"
        return out

    def append(self, *goals: str) -> None:
        """Append new goals to the list."""
        for goal in goals:
            logger.info(f'Adding new goal: "{goal.strip()}"')
            self.goals.append(goal.strip())

    def remove(self, *indices: int) -> None:
        """Remove goals from the list."""
        for index in sorted(indices, reverse=True):  # Last-to-first to avoid index shifting.
            logger.info(f'Removing goal: "{self.goals[index]}"')
            del self.goals[index]
