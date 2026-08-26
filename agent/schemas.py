"""Structured records owned by gameplay-agent state."""

from dataclasses import dataclass, field

# Pydantic resolves these dataclass annotations when it builds AgentState's persistence schema.
from common.enums import MapId  # noqa: TC001
from common.schemas import Coords  # noqa: TC001

_PUBLIC_LOG_MAX_ENTRIES = 100


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicLogEntry:
    """One entry displayed in the public stream log."""

    iteration: int
    content: str


@dataclass(slots=True, kw_only=True)
class PublicLog:
    """Bounded presentation log for the public stream."""

    entries: list[PublicLogEntry] = field(default_factory=list)

    def add(self, iteration: int, content: str) -> None:
        """Append one public entry and discard the oldest excess entry."""
        self.entries.append(PublicLogEntry(iteration=iteration, content=content))
        del self.entries[:-_PUBLIC_LOG_MAX_ENTRIES]


@dataclass(frozen=True, slots=True, kw_only=True)
class ScriptedDisplacementObservation:
    """A same-map destination reached while settling routine dialog."""

    iteration: int
    map_id: MapId
    destination: Coords
