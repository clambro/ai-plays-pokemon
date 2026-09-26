"""Domain tests for remembered connection-component checks."""

from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from agent.overworld.tools.inspect_map.schemas import MapInspectionResult, ResolvedConnection
from agent.overworld.tools.inspect_map.service import (
    get_connection_component,
    group_remembered_warps,
    inspect_map,
)
from common.enums import MapId, WarpActivation
from common.schemas import Coords
from database.map_boundary_memory.schemas import MapBoundaryMemoryRead
from database.map_memory.schemas import MapMemoryRead
from database.warp_memory.schemas import WarpMemoryRead

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def _connection_memory(
    destination_map: MapMemoryRead,
    warps: dict[MapId, list[WarpMemoryRead]],
    boundaries: dict[MapId, list[MapBoundaryMemoryRead]],
) -> Iterator[None]:
    """Supply isolated repository records for a multi-map connection check."""
    map_memories = {
        map_id: MapMemoryRead(map_id=map_id, terrain="", blockages={}) for map_id in warps
    }
    map_memories[destination_map.map_id] = destination_map
    warp_memories = {
        map_id: [warp.model_copy(update={"map_id": map_id}) for warp in records]
        for map_id, records in warps.items()
    }
    with (
        patch(
            "agent.overworld.tools.inspect_map.service.get_visited_maps",
            new=AsyncMock(return_value=list(map_memories)),
        ),
        patch(
            "agent.overworld.tools.inspect_map.service.get_map_memory",
            new=AsyncMock(side_effect=map_memories.get),
        ),
        patch(
            "agent.overworld.tools.inspect_map.service.get_warp_memories_for_map",
            new=AsyncMock(side_effect=lambda map_id: warp_memories.get(map_id, [])),
        ),
        patch(
            "agent.overworld.tools.inspect_map.service.get_warp_memories_to_map",
            new=AsyncMock(
                side_effect=lambda map_id: [
                    record
                    for records in warp_memories.values()
                    for record in records
                    if record.destination_map_id == map_id
                ]
            ),
        ),
        patch(
            "agent.overworld.tools.inspect_map.service.get_map_boundary_memories_for_map",
            new=AsyncMock(side_effect=lambda map_id: boundaries.get(map_id, [])),
        ),
        patch(
            "agent.overworld.tools.inspect_map.service.get_map_boundary_memories_to_map",
            new=AsyncMock(
                side_effect=lambda map_id: [
                    record
                    for records in boundaries.values()
                    for record in records
                    if record.destination_map_id == map_id
                ]
            ),
        ),
    ):
        yield


def _warp(
    warp_id: int,
    row: int,
    col: int,
    destination_map_id: MapId,
    destination_warp_id: int,
) -> WarpMemoryRead:
    return WarpMemoryRead(
        map_id=MapId.MT_MOON_B1F,
        warp_id=warp_id,
        row=row,
        col=col,
        destination_map_id=destination_map_id,
        destination_warp_id=destination_warp_id,
        activation=WarpActivation.STEP_ON,
        last_used_iteration=None,
    )


def _boundary(
    activation: WarpActivation,
    row: int,
    col: int,
    destination_map_id: MapId,
) -> MapBoundaryMemoryRead:
    return MapBoundaryMemoryRead(
        map_id=MapId.MT_MOON_B1F,
        activation=activation,
        row=row,
        col=col,
        destination_map_id=destination_map_id,
        destination_row=0,
        destination_col=0,
    )


def _connection(*coords: Coords, is_warp: bool = True) -> ResolvedConnection:
    """Build a resolved connection for component reachability checks."""
    return ResolvedConnection(
        source_map_id=MapId.MT_MOON_B1F,
        source_coords=coords,
        destination_map_id=MapId.ROUTE_4,
        destination_coords=(),
        is_warp=is_warp,
        activation=WarpActivation.STEP_ON if is_warp else None,
    )


@pytest.mark.unit
async def test_inspection_keeps_separate_arrival_regions() -> None:
    """Inspect all entrances without combining disconnected regions."""
    destination_map = MapMemoryRead(
        map_id=MapId.MT_MOON_B2F,
        terrain="▓▓▓▓▓▓▓\n▓∙∙∙∙∙▓\n▓▓▓▓▓▓▓\n▓∙∙∙∙∙▓\n▓░∙∙∙∙▓\n▓▓▓▓▓▓▓",
        blockages={},
    )
    warps = {
        MapId.MT_MOON_B1F: [
            _warp(0, 1, 1, MapId.MT_MOON_B2F, 0),
            _warp(1, 1, 2, MapId.MT_MOON_B2F, 0),
            _warp(1, 1, 2, MapId.MT_MOON_B2F, 2).model_copy(update={"last_used_iteration": 27}),
        ],
        MapId.MT_MOON_B2F: [
            _warp(0, 1, 1, MapId.MT_MOON_B1F, 0),
            _warp(1, 1, 3, MapId.MT_MOON_1F, 6),
            _warp(2, 3, 1, MapId.MT_MOON_B1F, 1),
            _warp(3, 3, 3, MapId.MT_MOON_1F, 4),
            _warp(5, 4, 4, MapId.MT_MOON_1F, 6),
        ],
        MapId.MT_MOON_1F: [
            _warp(4, 0, 0, MapId.MT_MOON_B2F, 3),
            _warp(5, 0, 1, MapId.MT_MOON_B2F, 3),
            _warp(6, 2, 0, MapId.MT_MOON_B2F, 5),
        ],
    }
    with _connection_memory(destination_map, warps, {}):
        results = await inspect_map(
            map_name=destination_map.map_id.name,
            hm_tiles=[],
        )

    assert isinstance(results, MapInspectionResult)
    assert tuple(arrival.arrival_coords for arrival in results.arrivals) == (
        Coords(row=1, col=1),
        Coords(row=1, col=3),
        Coords(row=3, col=1),
        Coords(row=3, col=3),
        Coords(row=4, col=4),
    )
    upper, _, result, _, _ = results.arrivals
    assert not upper.has_unexplored_terrain
    assert tuple(connection.source_coords for connection in upper.connections) == (
        (Coords(row=1, col=1),),
        (Coords(row=1, col=3),),
    )
    assert result.has_unexplored_terrain
    assert tuple(connection.source_coords for connection in result.connections) == (
        (Coords(row=3, col=1),),
        (Coords(row=3, col=3),),
        (Coords(row=4, col=4),),
    )
    assert tuple(connection.destination_coords for connection in result.connections) == (
        (Coords(row=1, col=1), Coords(row=1, col=2)),
        (Coords(row=0, col=0), Coords(row=0, col=1)),
        (Coords(row=2, col=0),),
    )
    assert tuple(connection.destination_map_id for connection in result.connections) == (
        MapId.MT_MOON_B1F,
        MapId.MT_MOON_1F,
        MapId.MT_MOON_1F,
    )


@pytest.mark.unit
async def test_check_boundary_preserves_pairs_and_distinguishes_unknown_destinations() -> None:
    """Keep boundary mappings while distinguishing unvisited maps from undiscovered landings."""
    source_map_id = MapId.MT_MOON_B1F
    destination_map_id = MapId.MT_MOON_B2F
    destination_map = MapMemoryRead(
        map_id=destination_map_id,
        terrain="▓▓▓▓▓▓\n▓∙∙∙∙▓\n▓∙∙∙∙▓\n▓▓▓▓▓▓",
        blockages={},
    )
    source_boundaries = [
        _boundary(WarpActivation.DOWN, 4, col, destination_map_id).model_copy(
            update={"destination_row": 1, "destination_col": col}
        )
        for col in (1, 3)
    ]
    return_boundary = _boundary(WarpActivation.UP, 1, 1, source_map_id).model_copy(
        update={"map_id": destination_map_id}
    )
    onward_boundary = _boundary(WarpActivation.DOWN, 2, 2, MapId.ROUTE_4).model_copy(
        update={"map_id": destination_map_id, "destination_row": 7, "destination_col": 8}
    )
    warps = {
        source_map_id: [],
        destination_map_id: [
            _warp(0, 1, 3, MapId.MT_MOON_1F, 0),
            _warp(1, 1, 4, MapId.ROUTE_4, 0),
        ],
        MapId.ROUTE_4: [],
    }
    boundaries = {
        source_map_id: source_boundaries,
        destination_map_id: [return_boundary, onward_boundary],
    }
    with _connection_memory(destination_map, warps, boundaries):
        results = await inspect_map(
            map_name=destination_map_id.name,
            hm_tiles=[],
        )

    assert isinstance(results, MapInspectionResult)
    assert tuple(arrival.arrival_coords for arrival in results.arrivals) == (
        Coords(row=1, col=1),
        Coords(row=1, col=3),
        Coords(row=1, col=4),
    )
    result = results.arrivals[0]
    assert all(arrival.has_recorded_access for arrival in results.arrivals)
    assert not result.has_unexplored_terrain
    assert tuple(connection.destination_map_id for connection in result.connections) == (
        None,
        MapId.ROUTE_4,
        source_map_id,
        MapId.ROUTE_4,
    )
    assert tuple(connection.destination_coords for connection in result.connections) == (
        (),
        (),
        (Coords(row=0, col=0),),
        (Coords(row=7, col=8),),
    )
    assert tuple(connection.is_warp for connection in result.connections) == (
        True,
        True,
        False,
        False,
    )


@pytest.mark.unit
async def test_inspection_includes_one_way_arrivals_without_return_connections() -> None:
    """An observed fall remains an arrival even without a return connection."""
    source_map_id = MapId.POKEMON_MANSION_3F
    destination_map_id = MapId.POKEMON_MANSION_2F
    destination_map = MapMemoryRead(
        map_id=destination_map_id,
        terrain="▓▓▓\n▓∙▓\n▓▓▓",
        blockages={},
    )
    holes = [
        _boundary(WarpActivation.STEP_ON, 4, col, destination_map_id).model_copy(
            update={
                "map_id": source_map_id,
                "destination_row": 1,
                "destination_col": 1,
            }
        )
        for col in (5, 8)
    ]
    warps = {source_map_id: [], destination_map_id: []}

    with _connection_memory(destination_map, warps, {source_map_id: holes}):
        results = await inspect_map(
            map_name=destination_map_id.name,
            hm_tiles=[],
        )

    assert isinstance(results, MapInspectionResult)
    assert len(results.arrivals) == 1
    assert results.arrivals[0].arrival_coords == Coords(row=1, col=1)
    assert results.arrivals[0].connections == ()
    assert not results.arrivals[0].has_unexplored_terrain


@pytest.mark.unit
async def test_elevator_arrival_exposes_all_observed_routes() -> None:
    """Keep both the return route and an onward route sharing the elevator's arrival doorway."""
    elevator = MapMemoryRead(
        map_id=MapId.ROCKET_HIDEOUT_ELEVATOR,
        terrain="▓▓▓▓▓▓\n▓∙∙∙∙▓\n▓∙∙∙∙▓\n▓▓▓▓▓▓",
        blockages={},
    )
    warps = {
        MapId.ROCKET_HIDEOUT_B1F: [_warp(4, 1, 1, MapId.ROCKET_HIDEOUT_ELEVATOR, 0)],
        MapId.ROCKET_HIDEOUT_B2F: [_warp(8, 1, 1, MapId.ROCKET_HIDEOUT_ELEVATOR, 0)],
        MapId.ROCKET_HIDEOUT_B4F: [_warp(9, 1, 1, MapId.ROCKET_HIDEOUT_ELEVATOR, 0)],
        MapId.ROCKET_HIDEOUT_ELEVATOR: [
            _warp(warp_id, 1, col, destination, landing)
            for warp_id, col in ((0, 2), (1, 3))
            for destination, landing in (
                (MapId.ROCKET_HIDEOUT_B1F, 4),
                (MapId.ROCKET_HIDEOUT_B2F, 8),
            )
        ],
    }
    with _connection_memory(elevator, warps, {}):
        results = await inspect_map(
            map_name=elevator.map_id.name,
            hm_tiles=[],
        )

    assert isinstance(results, MapInspectionResult)
    assert tuple(arrival.arrival_coords for arrival in results.arrivals) == (
        Coords(row=1, col=2),
        Coords(row=1, col=3),
    )
    result = results.arrivals[0]
    assert results.arrivals[1].connections == result.connections
    # B4F has an incoming route, but no elevator route to B4F has been observed.
    assert tuple(route.destination_map_id for route in result.connections) == (
        MapId.ROCKET_HIDEOUT_B1F,
        MapId.ROCKET_HIDEOUT_B2F,
    )
    assert all(
        route.source_coords == (Coords(row=1, col=2), Coords(row=1, col=3))
        for route in result.connections
    )


@pytest.mark.unit
@pytest.mark.parametrize("used_iteration", [None, 0])
async def test_inspection_preserves_directional_reachability(used_iteration: int | None) -> None:
    """An upper entrance can reach the lower region without implying a return route."""
    map_id = MapId.MT_MOON_B1F
    map_memory = MapMemoryRead(
        map_id=map_id,
        terrain="▓░▓▓▓\n▓∙∙∙▓\n▓▓▽▓▓\n▓∙∙∙▓\n▓▓▓▓▓",
        blockages={},
    )
    warps = {
        map_id: [
            _warp(0, 1, 1, MapId.ROUTE_4, 0).model_copy(
                update={"last_used_iteration": used_iteration}
            ),
            _warp(1, 3, 1, MapId.ROUTE_4, 1),
        ],
        MapId.ROUTE_4: [],
    }
    with _connection_memory(map_memory, warps, {}):
        result = await inspect_map(map_name=map_id.name, hm_tiles=[])

    assert isinstance(result, MapInspectionResult)
    upper, lower = result.arrivals
    assert upper.has_recorded_access is (used_iteration is not None)
    assert lower.has_recorded_access is (used_iteration is not None)
    assert tuple(connection.source_coords for connection in upper.connections) == (
        (Coords(row=1, col=1),),
        (Coords(row=3, col=1),),
    )
    assert tuple(connection.source_coords for connection in lower.connections) == (
        (Coords(row=3, col=1),),
    )
    assert upper.has_unexplored_terrain
    assert not lower.has_unexplored_terrain


@pytest.mark.unit
async def test_unused_incoming_route_establishes_access_without_inventing_a_reverse_path() -> None:
    """An unused one-way entry gives access to its region, not a region above its ledge."""
    map_id = MapId.MT_MOON_B1F
    memory = MapMemoryRead(
        map_id=map_id,
        terrain="▓▓▓▓▓\n▓∙∙∙▓\n▓▓▽▓▓\n▓∙∙∙▓\n▓▓▓▓▓",
        blockages={},
    )
    warps = {
        map_id: [
            _warp(0, 1, 1, MapId.ROUTE_4, 0),
            _warp(1, 3, 1, MapId.ROUTE_4, 1),
            _warp(2, 3, 3, MapId.ROUTE_4, 2),
        ],
        MapId.ROUTE_4: [],
        MapId.MT_MOON_1F: [_warp(0, 1, 1, map_id, 1)],
    }
    with _connection_memory(memory, warps, {}):
        result = await inspect_map(map_name=map_id.name, hm_tiles=[])

    assert isinstance(result, MapInspectionResult)
    assert tuple(arrival.has_recorded_access for arrival in result.arrivals) == (False, True, True)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("top_row", "expected_unexplored_terrain"),
    [("▓░▓▓▓", True), ("▓▓▓▓▓", False)],
)
def test_connection_check_lists_only_connections_in_the_arrival_component(
    top_row: str,
    *,
    expected_unexplored_terrain: bool,
) -> None:
    """Return complete connection groups only when their component is reachable."""
    connections = (
        _connection(Coords(row=1, col=1)),
        _connection(Coords(row=1, col=3)),
        _connection(Coords(row=3, col=3)),
        _connection(Coords(row=1, col=2), Coords(row=2, col=3), is_warp=False),
        _connection(Coords(row=3, col=2), is_warp=False),
    )
    map_memory = MapMemoryRead(
        map_id=MapId.MT_MOON_B1F,
        terrain=f"{top_row}\n▓∙∙∙▓\n▓▓▓▓▓\n▓∙∙∙▓\n▓▓▓▓▓",
        blockages={},
    )

    component = get_connection_component(
        arrival_coords=Coords(row=1, col=1),
        connections=connections,
        map_memory=map_memory,
        hm_tiles=[],
    )

    assert component.connections == (connections[0], connections[1], connections[3])
    assert component.has_unexplored_terrain is expected_unexplored_terrain


@pytest.mark.unit
@pytest.mark.parametrize("activation", [WarpActivation.DOWN, WarpActivation.STEP_ON])
def test_directional_warp_can_connect_remembered_terrain(activation: WarpActivation) -> None:
    """Walking across a directional entrance does not activate it like a step-on warp."""
    entrance = ResolvedConnection(
        source_map_id=MapId.MT_MOON_B1F,
        source_coords=(Coords(row=1, col=2),),
        destination_map_id=MapId.ROUTE_4,
        destination_coords=(),
        is_warp=True,
        activation=activation,
    )
    far_connection = _connection(Coords(row=1, col=3))
    map_memory = MapMemoryRead(
        map_id=MapId.MT_MOON_B1F,
        terrain="▓▓▓▓▓\n▓∙∙∙▓\n▓▓▓▓▓",
        blockages={},
    )

    component = get_connection_component(
        arrival_coords=Coords(row=1, col=1),
        connections=(entrance, far_connection),
        map_memory=map_memory,
        hm_tiles=[],
    )

    assert (far_connection in component.connections) is (activation == WarpActivation.DOWN)


@pytest.mark.unit
def test_connection_check_includes_unresolved_step_on_transition() -> None:
    """A reachable transition remains a connection before its destination is known."""
    map_memory = MapMemoryRead(
        map_id=MapId.POKEMON_MANSION_3F,
        terrain="▓▓▓▓▓\n▓∙○▓▓\n▓▓▓▓▓",
        blockages={},
    )

    component = get_connection_component(
        arrival_coords=Coords(row=1, col=1),
        connections=(),
        map_memory=map_memory,
        hm_tiles=[],
    )

    assert tuple(connection.source_coords for connection in component.connections) == (
        (Coords(row=1, col=2),),
    )
    assert component.connections[0].destination_map_id is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("row", "col", "destination", "activation", "grouped"),
    [
        (1, 2, MapId.ROCKET_HIDEOUT_ELEVATOR, WarpActivation.DOWN, True),
        (2, 1, MapId.ROCKET_HIDEOUT_ELEVATOR, WarpActivation.DOWN, True),
        (2, 2, MapId.ROCKET_HIDEOUT_ELEVATOR, WarpActivation.DOWN, False),
        (1, 3, MapId.ROCKET_HIDEOUT_ELEVATOR, WarpActivation.DOWN, False),
        (1, 2, MapId.ROUTE_4, WarpActivation.DOWN, False),
        (1, 2, MapId.ROCKET_HIDEOUT_ELEVATOR, WarpActivation.UP, False),
    ],
)
def test_connection_groups_preserve_individual_warp_destinations(
    row: int, col: int, destination: MapId, activation: WarpActivation, *, grouped: bool
) -> None:
    """Adjacent entrance tiles may have distinct landing records without losing their identity."""
    left = _warp(0, 1, 1, MapId.ROCKET_HIDEOUT_ELEVATOR, 0).model_copy(
        update={"activation": WarpActivation.DOWN}
    )
    right = _warp(1, row, col, destination, 1).model_copy(update={"activation": activation})

    groups = group_remembered_warps([right, left])

    assert groups == (((left, right),) if grouped else ((left,), (right,)))


@pytest.mark.unit
def test_connection_groups_follow_chains_without_merging_separate_entrances() -> None:
    """Group a whole contiguous entrance even when its warp IDs are out of spatial order."""
    left = _warp(0, 1, 1, MapId.ROCKET_HIDEOUT_ELEVATOR, 0)
    right = _warp(1, 1, 3, MapId.ROCKET_HIDEOUT_ELEVATOR, 1)
    middle = _warp(2, 1, 2, MapId.ROCKET_HIDEOUT_ELEVATOR, 2)
    separate = _warp(3, 3, 3, MapId.ROCKET_HIDEOUT_ELEVATOR, 3)

    groups = group_remembered_warps([separate, right, middle, left])

    assert groups == ((left, right, middle), (separate,))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("last_tile", "expected_unexplored_terrain"),
    [("░", True), ("●", False)],
)
def test_connection_check_recognizes_unresolved_spinner_exploration(
    last_tile: str,
    *,
    expected_unexplored_terrain: bool,
) -> None:
    """A spinner leading into unseen terrain keeps its arrival component explorable."""
    map_memory = MapMemoryRead(
        map_id=MapId.ROCKET_HIDEOUT_B3F,
        terrain=f"▓▓▓▓▓▓▓\n▓∙›∙∙{last_tile}▓\n▓▓▓▓▓▓▓",  # noqa: RUF001
        blockages={},
    )

    component = get_connection_component(
        arrival_coords=Coords(row=1, col=1),
        connections=(),
        map_memory=map_memory,
        hm_tiles=[],
    )

    assert component.has_unexplored_terrain is expected_unexplored_terrain
