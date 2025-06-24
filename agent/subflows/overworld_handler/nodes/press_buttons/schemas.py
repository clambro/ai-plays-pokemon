from pydantic import BaseModel

from common.enums import Button


class PressButtonsResponse(BaseModel):
    """The response from the overworld button presser prompt."""

    thoughts: str
    buttons: Button | list[Button]
