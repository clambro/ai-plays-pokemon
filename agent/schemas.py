"""Serializable records owned by gameplay-agent state."""

from dataclasses import dataclass

# Pydantic resolves these dataclass annotations when it builds AgentState's persistence schema.
from common.enums import MapId  # noqa: TC001
from common.schemas import Coords  # noqa: TC001


@dataclass(frozen=True, slots=True, kw_only=True)
class ScriptedDisplacementObservation:
    """A same-map destination reached while settling routine dialog."""

    iteration: int
    map_id: MapId
    destination: Coords
