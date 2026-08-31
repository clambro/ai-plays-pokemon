"""Data-transfer models for observed map-boundary memory."""

from pydantic import BaseModel, ConfigDict

from common.enums import FacingDirection, MapId


class MapBoundaryMemoryCreateUpdate(BaseModel):
    """One coordinate pair in a directly observed map connection."""

    map_id: MapId
    direction: FacingDirection
    row: int
    col: int
    destination_map_id: MapId
    destination_row: int
    destination_col: int


class MapBoundaryMemoryRead(MapBoundaryMemoryCreateUpdate):
    """A persisted map-boundary memory."""

    model_config = ConfigDict(from_attributes=True)
