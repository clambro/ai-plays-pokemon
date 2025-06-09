from pydantic import BaseModel, ConfigDict

from common.enums import MapId


class MapMemoryCreateUpdate(BaseModel):
    """Create/update model for a map memory."""

    map_id: MapId
    tiles: str
    iteration: int


class MapMemoryRead(BaseModel):
    """Read model for a map memory."""

    map_id: MapId
    tiles: str

    model_config = ConfigDict(from_attributes=True)
