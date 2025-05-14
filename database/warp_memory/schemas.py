from pydantic import BaseModel, ConfigDict

from emulator.enums import MapLocation


class WarpMemory(BaseModel):
    """Read/create model for a warp memory."""

    map_id: MapLocation
    warp_id: int
    description: str

    model_config = ConfigDict(from_attributes=True)
