"""Resolved results of remembered connection checks."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from common.enums import MapId
    from common.schemas import Coords
    from database.map_boundary_memory.schemas import MapBoundaryMemoryRead
    from database.warp_memory.schemas import WarpMemoryRead

type WarpGroups = tuple[tuple[WarpMemoryRead, ...], ...]
type SourceConnection = WarpMemoryRead | tuple[MapBoundaryMemoryRead, ...]


class ConnectionCheckError(Enum):
    """Reasons a requested connection cannot be inspected."""

    INVALID_MAP = auto()
    UNSUPPORTED_MAP = auto()
    UNVISITED_MAP = auto()
    UNKNOWN_CONNECTION = auto()
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
class ConnectionCheckResult:
    """The checked connection and other connections reachable from its arrival point."""

    connection: ResolvedConnection
    other_connections: tuple[ResolvedConnection, ...] = ()
    has_unexplored_terrain: bool = False
