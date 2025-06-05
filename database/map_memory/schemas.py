from pydantic import BaseModel, ConfigDict


class MapMemoryCreateUpdate(BaseModel):
    """Create/update model for a map memory."""

    map_id: int
    tiles: str
    iteration: int


class MapMemoryRead(BaseModel):
    """Read model for a map memory."""

    map_id: int
    tiles: str

    model_config = ConfigDict(from_attributes=True)
