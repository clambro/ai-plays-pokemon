from pydantic import BaseModel

from emulator.enums import Button


class DecisionMakerTextResponse(BaseModel):
    """The response from the text decision maker prompt."""

    thoughts: str
    button: Button
