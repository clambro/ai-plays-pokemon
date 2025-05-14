from pydantic import BaseModel


class MapMemory(BaseModel):
    """Read/create model for a map memory."""

    map_id: int
    tiles: str
