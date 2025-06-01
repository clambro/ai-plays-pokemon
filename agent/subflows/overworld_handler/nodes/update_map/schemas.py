from pydantic import BaseModel


class EntityUpdate(BaseModel):
    """An update to an entity."""

    index: int
    description: str


class UpdateEntitiesResponse(BaseModel):
    """Response to the update onscreen entities prompts."""

    updates: list[EntityUpdate]
