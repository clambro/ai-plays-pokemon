from pydantic import BaseModel


class UpdateGoalsResponse(BaseModel):
    """The response to the update goals prompt."""

    remove: list[int]
    append: list[str]
