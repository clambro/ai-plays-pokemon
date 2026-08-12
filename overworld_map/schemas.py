"""Data models for the explored overworld map."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from common.enums import BlockedDirection, MapId
    from common.schemas import Coords
    from emulator.parsers.map import MapConnection


@dataclass(slots=True, kw_only=True)
class OverworldMap:
    """A map of a particular region of the overworld."""

    id: MapId
    ascii_tiles: list[list[str]]
    blockages: dict[Coords, BlockedDirection]
    known_sprite_ids: set[int]
    known_sign_ids: set[int]
    known_warp_ids: set[int]
    known_map_ids: frozenset[MapId]
    north_connection: MapConnection | None
    south_connection: MapConnection | None
    east_connection: MapConnection | None
    west_connection: MapConnection | None

    @property
    def height(self) -> int:
        """The height of the map."""
        return len(self.ascii_tiles)

    @property
    def width(self) -> int:
        """The width of the map."""
        return len(self.ascii_tiles[0])

    @property
    def ascii_tiles_ndarray(self) -> np.ndarray:
        """The ascii tiles as a numpy array."""
        return np.array(self.ascii_tiles)

    @property
    def ascii_tiles_str(self) -> str:
        """The ascii tiles as a string."""
        return "\n".join("".join(row) for row in self.ascii_tiles)
