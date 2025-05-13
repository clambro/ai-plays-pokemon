from pydantic import BaseModel


class WarpMemoryCreate(BaseModel):
    """Create model for a new warp memory."""

    map_id: int
    warp_id: int
    description: str = "No description added yet."


class WarpMemoryRead(BaseModel):
    """Pydantic schema for a warp memory from the database."""

    map_id: int
    warp_id: int
    description: str
