from pydantic import BaseModel, ConfigDict

from emulator.enums import MapLocation


class SpriteMemoryCreate(BaseModel):
    """Create/update model for a sprite memory."""

    map_id: MapLocation
    sprite_id: int
    iteration: int


class SpriteMemoryUpdate(BaseModel):
    """Create/update model for a sprite memory."""

    map_id: MapLocation
    sprite_id: int
    description: str
    iteration: int


class SpriteMemoryRead(BaseModel):
    """Read model for a sprite memory."""

    map_id: MapLocation
    sprite_id: int
    description: str | None

    model_config = ConfigDict(from_attributes=True)
