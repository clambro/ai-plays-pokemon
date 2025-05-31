from pydantic import BaseModel


class ShouldCritiqueResponse(BaseModel):
    """The response from the should critique prompt."""

    thoughts: str
    should_critique: bool
