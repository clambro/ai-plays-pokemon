from pydantic import BaseModel, ConfigDict

from emulator.enums import MapLocation


class SpriteMemoryCreateUpdate(BaseModel):
    """Create/update model for a sprite memory."""

    map_id: MapLocation
    sprite_id: int
    description: str
    iteration: int

    model_config = ConfigDict(from_attributes=True)


class SpriteMemoryRead(BaseModel):
    """Read model for a sprite memory."""

    map_id: MapLocation
    sprite_id: int
    description: str

    model_config = ConfigDict(from_attributes=True)
