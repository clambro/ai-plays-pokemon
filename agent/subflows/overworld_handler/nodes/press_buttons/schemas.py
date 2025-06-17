from pydantic import BaseModel

from emulator.enums import Button


class PressButtonsResponse(BaseModel):
    """The response from the overworld button presser prompt."""

    thoughts: str
    buttons: Button | list[Button]
