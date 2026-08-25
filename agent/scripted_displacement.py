"""Recognition of repeated ROM-controlled player displacement."""

from typing import TYPE_CHECKING

from agent.schemas import ScriptedDisplacementObservation

if TYPE_CHECKING:
    from agent.state import AgentState
    from common.enums import MapId
    from common.schemas import Coords

WINDOW_ITERATIONS = 20
REPETITION_THRESHOLD = 3


def record_scripted_displacement(
    state: AgentState,
    *,
    map_id: MapId,
    destination: Coords,
) -> str | None:
    """Record a dialog-owned displacement and flag a repeated destination.

    Args:
        state: Mutable gameplay state that owns the observation history.
        map_id: Map on which the displacement began and ended.
        destination: Player location after overworld control returned.

    Returns:
        A gameplay advisory once the destination has occurred at least three
        times in the rolling iteration window, otherwise ``None``.
    """
    earliest_iteration = state.iteration - WINDOW_ITERATIONS + 1
    recent_observations = [
        observation
        for observation in state.scripted_displacements
        if earliest_iteration <= observation.iteration <= state.iteration
    ]
    observation = ScriptedDisplacementObservation(
        iteration=state.iteration,
        map_id=map_id,
        destination=destination,
    )
    state.scripted_displacements = [*recent_observations, observation][-WINDOW_ITERATIONS:]

    matching_observations = sum(
        previous.map_id == map_id and previous.destination == destination
        for previous in state.scripted_displacements
    )
    if matching_observations < REPETITION_THRESHOLD:
        return None
    return (
        "I have repeatedly been moved back to the same location by a scripted event in quick"
        " succession. This means I am likely pursuing the wrong path. I should try something"
        " different. There is no way to sneak past a scripted event."
    )
