from pydantic import BaseModel, ConfigDict

from emulator.enums import MapLocation


class SignMemoryCreateUpdate(BaseModel):
    """Create/update model for a sign memory."""

    map_id: MapLocation
    sign_id: int
    description: str
    iteration: int


class SignMemoryRead(BaseModel):
    """Read model for a sign memory."""

    map_id: MapLocation
    sign_id: int
    description: str

    model_config = ConfigDict(from_attributes=True)
