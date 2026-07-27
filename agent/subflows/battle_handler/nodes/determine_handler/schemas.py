"""Data models for determine handler in the battle subflow."""

from pydantic import BaseModel


class DetermineArgsResponse(BaseModel):
    """The response from the determine args node."""

    thoughts: str
    index: int
