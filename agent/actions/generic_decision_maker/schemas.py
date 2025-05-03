from pydantic import BaseModel

from emulator.enums import Button


class GenericDecisionMakerResponse(BaseModel):
    """The response from the generic decision maker."""

    thoughts: str
    button: Button
