from pydantic import BaseModel, ConfigDict

from common.enums import MapEntityType
from emulator.enums import MapLocation


class MapEntityMemoryCreate(BaseModel):
    """Create model for a map entity memory."""

    map_id: MapLocation
    entity_id: int
    entity_type: MapEntityType
    iteration: int


class MapEntityMemoryUpdate(BaseModel):
    """Update model for a map entity memory."""

    map_id: MapLocation
    entity_id: int
    entity_type: MapEntityType
    description: str
    iteration: int


class MapEntityMemoryRead(BaseModel):
    """Read model for a map entity memory."""

    map_id: MapLocation
    entity_id: int
    entity_type: MapEntityType
    description: str | None

    model_config = ConfigDict(from_attributes=True)
