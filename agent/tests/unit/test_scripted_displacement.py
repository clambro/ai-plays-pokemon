"""Behavior tests for repeated ROM-controlled displacement."""

import json
from typing import TYPE_CHECKING

import pytest

from agent.dialog import _record_scripted_displacement
from agent.state import AgentState
from common.enums import MapId
from common.schemas import Coords

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED_HISTORY_LIMIT = 20


def _record(
    state: AgentState,
    *,
    iteration: int,
    map_id: MapId = MapId.ROUTE_3,
    destination: Coords | None = None,
) -> str | None:
    """Record one observation at a chosen application iteration."""
    state.iteration = iteration
    return _record_scripted_displacement(
        state,
        map_id=map_id,
        destination=destination or Coords(row=3, col=4),
    )


@pytest.mark.unit
def test_third_matching_destination_in_twenty_iterations_is_flagged(tmp_path: Path) -> None:
    """Require three arrivals at the same map-qualified tile."""
    state = AgentState(folder=tmp_path)

    assert _record(state, iteration=1) is None
    assert _record(state, iteration=2) is None
    assert _record(state, iteration=3, map_id=MapId.ROUTE_2) is None
    assert _record(state, iteration=4, destination=Coords(row=4, col=3)) is None
    assert _record(state, iteration=20) is not None


@pytest.mark.unit
def test_destination_observations_expire_after_twenty_iterations(tmp_path: Path) -> None:
    """Do not flag repetition based on destinations outside the rolling window."""
    state = AgentState(folder=tmp_path)

    assert _record(state, iteration=1) is None
    assert _record(state, iteration=2) is None
    assert _record(state, iteration=21) is None


@pytest.mark.unit
def test_displacement_history_never_exceeds_twenty_observations(tmp_path: Path) -> None:
    """Bound retained history even if several arrivals share one iteration."""
    state = AgentState(folder=tmp_path)

    for row in range(25):
        _record(
            state,
            iteration=1,
            destination=Coords(row=row, col=0),
        )

    assert len(state.scripted_displacements) == EXPECTED_HISTORY_LIMIT


@pytest.mark.unit
def test_displacement_history_round_trips_and_defaults_for_old_backups(tmp_path: Path) -> None:
    """Persist the small history without making old state files invalid."""
    state = AgentState(folder=tmp_path)
    assert _record(state, iteration=1) is None
    assert _record(state, iteration=2) is None

    restored_state = AgentState.model_validate_json(state.model_dump_json())
    old_state = AgentState.model_validate_json(json.dumps({"folder": str(tmp_path)}))

    assert _record(restored_state, iteration=3) is not None
    assert _record(old_state, iteration=1) is None
    assert _record(old_state, iteration=2) is None
    assert _record(old_state, iteration=3) is not None
