from pydantic import BaseModel

from memory.goals import Goal


class UpdateGoalsResponse(BaseModel):
    """The response to the update goals prompt."""

    remove: list[int]
    append: list[Goal]
