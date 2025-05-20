from pydantic import BaseModel, ConfigDict

from emulator.enums import MapLocation


class SignMemoryCreate(BaseModel):
    """Create/update model for a sign memory."""

    map_id: MapLocation
    sign_id: int
    iteration: int


class SignMemoryUpdate(BaseModel):
    """Create/update model for a sign memory."""

    map_id: MapLocation
    sign_id: int
    description: str
    iteration: int


class SignMemoryRead(BaseModel):
    """Read model for a sign memory."""

    map_id: MapLocation
    sign_id: int
    description: str | None

    model_config = ConfigDict(from_attributes=True)
