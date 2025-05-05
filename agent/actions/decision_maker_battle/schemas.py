from pydantic import BaseModel

from emulator.enums import Button


class DecisionMakerBattleResponse(BaseModel):
    """The response from the battle decision maker prompt."""

    thoughts: str
    button: Button
