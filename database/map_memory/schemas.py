"""Data-transfer models for map memory."""

from pydantic import BaseModel, ConfigDict

from common.enums import BlockedDirection, MapId
from common.schemas import Coords


class MapMemoryCreateUpdate(BaseModel):
    """Create/update model for a map memory."""

    map_id: MapId
    terrain: str
    blockages: dict[str, BlockedDirection]
    iteration: int


class MapMemoryRead(BaseModel):
    """Read model for a map memory."""

    map_id: MapId
    terrain: str
    blockages: dict[Coords, BlockedDirection]

    model_config = ConfigDict(from_attributes=True)
