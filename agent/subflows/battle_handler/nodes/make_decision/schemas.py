"""Data models for make decision in the battle subflow."""

from pydantic import BaseModel

from common.enums import Button


class MakeDecisionResponse(BaseModel):
    """The response from the battle handler make decision prompt."""

    thoughts: str
    buttons: list[Button]

    def __str__(self) -> str:
        """Return a human-readable representation."""
        return f"{self.thoughts} Pressed the following button(s): {[str(b) for b in self.buttons]}."
