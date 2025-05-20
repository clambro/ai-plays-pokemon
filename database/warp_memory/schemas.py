from pydantic import BaseModel, ConfigDict

from emulator.enums import MapLocation


class WarpMemoryUpdate(BaseModel):
    """Create/update model for a warp memory."""

    map_id: MapLocation
    warp_id: int
    description: str
    iteration: int


class WarpMemoryCreate(BaseModel):
    """Create/update model for a warp memory."""

    map_id: MapLocation
    warp_id: int
    iteration: int


class WarpMemoryRead(BaseModel):
    """Read model for a warp memory."""

    map_id: MapLocation
    warp_id: int
    description: str | None

    model_config = ConfigDict(from_attributes=True)
