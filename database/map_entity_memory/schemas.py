"""Data-transfer models for map entity memory."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common.enums import MapEntityType, MapId


class MapEntityMemoryCreate(BaseModel):
    """Create model for a map entity memory."""

    map_id: MapId
    entity_id: int
    entity_type: MapEntityType


class MapEntityMemoryRead(BaseModel):
    """Read model for a map entity memory."""

    map_id: MapId
    entity_id: int
    entity_type: MapEntityType
    last_interaction: Annotated[str, Field(min_length=1)] | None
    last_interaction_iteration: int | None

    model_config = ConfigDict(from_attributes=True)


class MapEntityMemoryInteractionUpdate(BaseModel):
    """A literal interaction observation for one persisted map entity."""

    map_id: MapId
    entity_id: int
    entity_type: MapEntityType
    last_interaction: Annotated[str, Field(min_length=1)]
    last_interaction_iteration: int


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
