"""Internal data structures for cross-map route recall."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from common.enums import AsciiTile, MapId
    from common.schemas import Coords


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteSearchState:
    """Current location and traversal knowledge used for one route search."""

    map_id: MapId
    coords: Coords
    reachable_coords: frozenset[Coords]
    hm_tiles: list[AsciiTile]
    visited_map_ids: frozenset[MapId]
