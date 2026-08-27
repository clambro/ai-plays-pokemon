"""Data-transfer models for warp memory."""

from pydantic import BaseModel, ConfigDict

from common.enums import MapId, WarpActivation


class WarpMemoryCreateUpdate(BaseModel):
    """A discovered warp and its currently observed destination."""

    map_id: MapId
    warp_id: int
    row: int
    col: int
    destination_map_id: MapId
    destination_warp_id: int
    activation: WarpActivation


class WarpMemoryRead(WarpMemoryCreateUpdate):
    """A persisted warp memory."""

    last_used_iteration: int | None

    model_config = ConfigDict(from_attributes=True)
