"""Data models for the explored overworld map."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from common.enums import BlockedDirection, MapId
    from common.schemas import Coords
    from emulator.parsers.map import MapConnection


@dataclass(frozen=True, slots=True, kw_only=True)
class MapEntityInteractionMemory:
    """Last literal interaction observed for one map entity."""

    text: str
    iteration: int


@dataclass(slots=True, kw_only=True)
class OverworldMap:
    """Persistent explored terrain and discoveries for one overworld map."""

    id: MapId
    terrain: list[list[str]]
    blockages: dict[Coords, BlockedDirection]
    known_sprite_ids: set[int]
    sprite_interactions: dict[int, MapEntityInteractionMemory]
    known_sign_ids: set[int]
    sign_interactions: dict[int, MapEntityInteractionMemory]
    known_warp_ids: set[int]
    warp_usage_iterations: dict[int, int]
    known_map_ids: frozenset[MapId]
    north_connection: MapConnection | None
    south_connection: MapConnection | None
    east_connection: MapConnection | None
    west_connection: MapConnection | None

    @property
    def height(self) -> int:
        """The height of the map."""
        return len(self.terrain)

    @property
    def width(self) -> int:
        """The width of the map."""
        return len(self.terrain[0])

    @property
    def terrain_ndarray(self) -> np.ndarray:
        """Return the terrain as a NumPy array."""
        return np.asarray(self.terrain)

    @property
    def terrain_str(self) -> str:
        """Return the serialized terrain."""
        return "\n".join("".join(row) for row in self.terrain)
