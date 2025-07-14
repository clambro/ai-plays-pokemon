from pydantic import BaseModel

from common.schemas import Coords


class SokobanMap(BaseModel):
    """A simplified map of the Sokoban puzzle."""

    tiles: list[list[str]]
    boulders: set[Coords]
    goals: set[Coords]
