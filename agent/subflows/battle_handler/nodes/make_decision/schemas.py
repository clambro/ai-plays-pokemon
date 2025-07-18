from pydantic import BaseModel

from common.enums import Button


class MakeDecisionResponse(BaseModel):
    """The response from the battle handler make decision prompt."""

    thoughts: str
    buttons: list[Button]

    def __str__(self) -> str:
        return f"{self.thoughts} Pressed the following button(s): {self.buttons}."
