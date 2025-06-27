from pydantic import BaseModel


class DetermineArgsResponse(BaseModel):
    """The response from the determine args node."""

    thoughts: str
    index: int
