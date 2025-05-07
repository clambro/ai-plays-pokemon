from pydantic import BaseModel, Field


class Goals(BaseModel):
    """The goals for the agent."""

    goals: list[str] = Field(default_factory=list)

    def __str__(self) -> str:
        """Return a string representation of the goals."""
        if not self.goals:
            return ""
        out = (
            "Here are the goals that you have set for yourself. Your ultimate goal is, of course,"
            " to become the Elite Four Champion, but these goals here are the next steps on your"
            " journey to that goal."
        )
        out += "\n<goals>\n"
        out += "\n".join(f"[{i}] {g}" for i, g in enumerate(self.goals))
        out += "\n</goals>"
        return out

    def append(self, goal: str) -> None:
        """Append new goals to the list."""
        self.goals.append(goal.strip())

    def remove(self, index: int) -> None:
        """Remove a goal from the list."""
        del self.goals[index]

    def edit(self, index: int, goal: str) -> None:
        """Edit a goal in the list."""
        self.goals[index] = goal.strip()
