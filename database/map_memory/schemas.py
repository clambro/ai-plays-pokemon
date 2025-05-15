from pydantic import BaseModel, ConfigDict

from emulator.enums import MapLocation


class MapMemoryCreateUpdate(BaseModel):
    """Create/update model for a map memory."""

    map_id: MapLocation
    tiles: str
    iteration: int

    model_config = ConfigDict(from_attributes=True)


class MapMemoryRead(BaseModel):
    """Read model for a map memory."""

    map_id: MapLocation
    tiles: str

    model_config = ConfigDict(from_attributes=True)
