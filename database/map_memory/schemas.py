from pydantic import BaseModel, ConfigDict

from emulator.enums import MapLocation


class MapMemory(BaseModel):
    """Read/create model for a map memory."""

    map_id: MapLocation
    tiles: str

    model_config = ConfigDict(from_attributes=True)
