from pydantic import BaseModel

from emulator.enums import MapLocation


class WarpMemory(BaseModel):
    """Read/create model for a warp memory."""

    map_id: MapLocation
    warp_id: int
    description: str
