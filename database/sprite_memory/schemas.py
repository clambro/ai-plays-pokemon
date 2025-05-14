from pydantic import BaseModel

from emulator.enums import MapLocation


class SpriteMemory(BaseModel):
    """Read/create model for a sprite memory."""

    map_id: MapLocation
    sprite_id: int
    description: str
