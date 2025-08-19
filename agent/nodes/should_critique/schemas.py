from pydantic import BaseModel


class ShouldCritiqueResponse(BaseModel):
    """The response from the should critique prompt."""

    thoughts: str
    is_stuck: bool
