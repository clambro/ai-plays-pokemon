from pydantic import BaseModel

from emulator.enums import Button


class DecisionMakerOverworldResponse(BaseModel):
    """The response from the overworld decision maker prompt."""

    thoughts: str
    button: Button
