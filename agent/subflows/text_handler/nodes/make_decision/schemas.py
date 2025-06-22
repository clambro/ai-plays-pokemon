from pydantic import BaseModel

from common.enums import Button


class DecisionMakerTextResponse(BaseModel):
    """The response from the text decision maker prompt."""

    thoughts: str
    buttons: Button | list[Button]
