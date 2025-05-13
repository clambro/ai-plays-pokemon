from pydantic import BaseModel


class KnownWarpCreate(BaseModel):
    """Create model for a new known warp."""

    map_id: int
    warp_id: int
    y: int
    x: int
    destination: int
    description: str = "No description added yet."


class KnownWarpRead(BaseModel):
    """Pydantic schema for a known warp from the database."""

    map_id: int
    warp_id: int
    y: int
    x: int
    destination: int
    description: str
