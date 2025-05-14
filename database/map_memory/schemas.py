from pydantic import BaseModel

from emulator.enums import MapLocation


class MapMemory(BaseModel):
    """Read/create model for a map memory."""

    map_id: MapLocation
    tiles: str
