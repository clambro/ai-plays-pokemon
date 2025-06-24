from pydantic import BaseModel, ConfigDict

from common.enums import BlockedDirection, MapId
from common.schemas import Coords


class MapMemoryCreateUpdate(BaseModel):
    """Create/update model for a map memory."""

    map_id: MapId
    tiles: str
    blockages: dict[Coords, BlockedDirection]
    iteration: int


class MapMemoryRead(BaseModel):
    """Read model for a map memory."""

    map_id: MapId
    tiles: str
    blockages: dict[Coords, BlockedDirection]

    model_config = ConfigDict(from_attributes=True)
