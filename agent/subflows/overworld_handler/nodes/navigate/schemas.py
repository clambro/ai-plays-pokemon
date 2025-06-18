from pydantic import BaseModel

from common.schemas import Coords


class NavigationResponse(BaseModel):
    """The response from the overworld navigation prompt."""

    thoughts: str
    coords: Coords
