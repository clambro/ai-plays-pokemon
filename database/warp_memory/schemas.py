from pydantic import BaseModel


class WarpMemory(BaseModel):
    """Read/create model for a warp memory."""

    map_id: int
    warp_id: int
    description: str
