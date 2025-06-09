from pydantic import BaseModel, ConfigDict, field_validator

from common.enums import MapEntityType, MapId


class MapEntityMemoryCreate(BaseModel):
    """Create model for a map entity memory."""

    map_id: MapId
    entity_id: int
    entity_type: MapEntityType
    iteration: int


class MapEntityMemoryUpdate(BaseModel):
    """Update model for a map entity memory."""

    map_id: MapId
    entity_id: int
    entity_type: MapEntityType
    description: str
    iteration: int


class MapEntityMemoryRead(BaseModel):
    """Read model for a map entity memory."""

    map_id: MapId
    entity_id: int
    entity_type: MapEntityType
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class MapEntityMemoryDelete(BaseModel):
    """Delete model for a map entity memory."""

    map_id: MapId
    entity_id: int
    entity_type: MapEntityType

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: MapEntityType) -> MapEntityType:
        """Validate the entity type."""
        if v != MapEntityType.SPRITE:
            raise ValueError("Only sprite memories can be deleted.")
        return v
