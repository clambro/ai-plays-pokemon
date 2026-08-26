"""Data-transfer models for observed route transitions."""

from pydantic import BaseModel

from common.enums import Button, MapId, WarpActivation
from common.schemas import Coords


class RouteTransitionCreate(BaseModel):
    """A directed transition observed at an external overworld boundary."""

    source_map_id: MapId
    source_coords: Coords
    button: Button
    warp_activation: WarpActivation | None
    destination_map_id: MapId
    destination_coords: Coords


class RouteTransitionRead(RouteTransitionCreate):
    """A persisted route transition."""

    create_iteration: int
