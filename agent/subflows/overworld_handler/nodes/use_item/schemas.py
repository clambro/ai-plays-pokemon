from pydantic import BaseModel, Field


class UseItemError(Exception):
    """An error that occurs when using an item."""


class UseItemResponse(BaseModel):
    """The response from the overworld use item prompt."""

    thoughts: str
    index: int = Field(ge=0)
