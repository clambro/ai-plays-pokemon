"""Data models for the explored overworld map."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from common.enums import BlockedDirection, MapId
from emulator.parsers.sign import Sign
from emulator.parsers.sprite import Sprite
from emulator.parsers.warp import Warp

if TYPE_CHECKING:
    from common.schemas import Coords


class OverworldSprite(Sprite):
    """A sprite on the overworld map, known to the player."""

    @classmethod
    def from_sprite(cls, sprite: Sprite) -> OverworldSprite:
        """Create an overworld sprite from parsed sprite state."""
        return cls(**sprite.model_dump())


class OverworldSign(Sign):
    """A sign on the overworld map, known to the player."""

    @classmethod
    def from_sign(cls, sign: Sign) -> OverworldSign:
        """Create an overworld sign from parsed sign state."""
        return cls(**sign.model_dump())


class OverworldWarp(Warp):
    """A warp on the overworld map, known to the player."""

    visited: bool

    @classmethod
    def from_warp(cls, warp: Warp, visited_maps: list[MapId]) -> OverworldWarp:
        """Create an overworld warp from a warp."""
        # The OUTSIDE placeholder map is not in the DB, so we assume it's always visited.
        visited = warp.destination in visited_maps or warp.destination == MapId.OUTSIDE
        return cls(**warp.model_dump(), visited=visited)


@dataclass(slots=True, kw_only=True)
class OverworldMap:
    """A map of a particular region of the overworld."""

    id: MapId
    ascii_tiles: list[list[str]]
    blockages: dict[Coords, BlockedDirection]
    known_sprites: dict[int, OverworldSprite]
    known_signs: dict[int, OverworldSign]
    known_warps: dict[int, OverworldWarp]
    north_connection: MapId | None
    south_connection: MapId | None
    east_connection: MapId | None
    west_connection: MapId | None

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
