"""Data models for the overworld Sokoban solver tool."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from common.schemas import Coords


@dataclass(slots=True, kw_only=True)
class SokobanMap:
    """A simplified map of the Sokoban puzzle."""

    tiles: list[list[str]]
    boulders: set[Coords]
    goals: set[Coords]
