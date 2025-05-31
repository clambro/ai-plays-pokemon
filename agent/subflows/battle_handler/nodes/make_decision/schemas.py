from pydantic import BaseModel

from emulator.enums import Button


class MakeDecisionResponse(BaseModel):
    """The response from the battle handler make decision prompt."""

    thoughts: str
    button: Button

    def __str__(self) -> str:
        return f'{self.thoughts} Pressed the "{self.button}" button.'
