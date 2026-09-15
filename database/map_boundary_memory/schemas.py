"""Data-transfer models for observed coordinate-based map connections."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from common.enums import MapId, WarpActivation


@dataclass(frozen=True, slots=True, kw_only=True)
class MapBoundaryGroupKey:
    """Identity shared by map-boundary records that form one connection."""

    map_id: MapId
    activation: WarpActivation
    destination_map_id: MapId
    source_row: int | None
    source_col: int | None


class MapBoundaryMemoryCreateUpdate(BaseModel):
    """One coordinate pair in a directly observed map connection."""

    map_id: MapId
    activation: WarpActivation
    row: int
    col: int
    destination_map_id: MapId
    destination_row: int
    destination_col: int


class MapBoundaryMemoryRead(MapBoundaryMemoryCreateUpdate):
    """A persisted coordinate-based map connection."""

    model_config = ConfigDict(from_attributes=True)
