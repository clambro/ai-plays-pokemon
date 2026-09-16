"""Typed results of remembered map inspections."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from common.enums import MapId
    from common.schemas import Coords
    from database.map_boundary_memory.schemas import MapBoundaryMemoryRead
    from database.warp_memory.schemas import WarpMemoryRead

type WarpGroups = tuple[tuple[WarpMemoryRead, ...], ...]


class MapInspectionError(Enum):
    """Reasons a requested map cannot be inspected."""

    INVALID_MAP = auto()
    UNSUPPORTED_MAP = auto()
    UNVISITED_MAP = auto()
    MEMORY_UNAVAILABLE = auto()


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedConnection:
    """A connection's known endpoints and usage, with no remaining destination lookup."""

    source_map_id: MapId
    source_coords: tuple[Coords, ...]
    destination_map_id: MapId | None
    destination_coords: tuple[Coords, ...]
    is_warp: bool
    last_used_iteration: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ConnectionComponent:
    """Remembered map features reachable from one arrival point."""

    warp_groups: WarpGroups
    boundary_groups: tuple[tuple[MapBoundaryMemoryRead, ...], ...]
    has_unexplored_terrain: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class MapArrivalInspection:
    """Options at an entrance, including whether a known entry can reach its coordinate."""

    arrival_coords: Coords
    has_recorded_access: bool
    connections: tuple[ResolvedConnection, ...]
    has_unexplored_terrain: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class MapInspectionResult:
    """All discovered entrances and observed coordinate-based arrivals on a visited map."""

    map_id: MapId
    arrivals: tuple[MapArrivalInspection, ...]
