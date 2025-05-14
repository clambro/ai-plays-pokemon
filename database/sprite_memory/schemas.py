from pydantic import BaseModel


class SpriteMemory(BaseModel):
    """Read/create model for a sprite memory."""

    map_id: int
    sprite_id: int
    description: str
