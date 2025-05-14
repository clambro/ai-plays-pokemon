from pydantic import BaseModel, ConfigDict

from emulator.enums import MapLocation


class SpriteMemory(BaseModel):
    """Read/create model for a sprite memory."""

    map_id: MapLocation
    sprite_id: int
    description: str

    model_config = ConfigDict(from_attributes=True)
