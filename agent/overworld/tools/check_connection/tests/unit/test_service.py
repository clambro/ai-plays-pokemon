"""Domain tests for remembered connection-component checks."""

from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from agent.overworld.tools.check_connection.service import (
    check_connection,
    get_connection_component,
    group_remembered_warps,
)
from common.enums import FacingDirection, MapId, WarpActivation
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
            "agent.overworld.tools.check_connection.service.get_visited_maps",
            new=AsyncMock(return_value=list(map_memories)),
        ),
        patch(
            "agent.overworld.tools.check_connection.service.get_map_memory",
            new=AsyncMock(side_effect=map_memories.get),
        ),
        patch(
            "agent.overworld.tools.check_connection.service.get_warp_memories_for_map",
            new=AsyncMock(side_effect=lambda map_id: warp_memories.get(map_id, [])),
        ),
        patch(
            "agent.overworld.tools.check_connection.service.get_map_boundary_memories_for_map",
            new=AsyncMock(side_effect=lambda map_id: boundaries.get(map_id, [])),
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
    direction: FacingDirection,
    row: int,
    col: int,
    destination_map_id: MapId,
) -> MapBoundaryMemoryRead:
    return MapBoundaryMemoryRead(
        map_id=MapId.MT_MOON_B1F,
        direction=direction,
        row=row,
        col=col,
        destination_map_id=destination_map_id,
        destination_row=0,
        destination_col=0,
    )


@pytest.mark.unit
async def test_check_warp_keeps_alternative_arrival_regions_separate() -> None:
    """Retain multiple routes from one tile without combining their arrival regions or usage."""
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
        results = await check_connection(
            map_name=MapId.MT_MOON_B1F.name,
            coordinates=Coords(row=1, col=2),
            hm_tiles=[],
        )

    assert isinstance(results, list)
    upper, result = results
    assert upper.connection.destination_coords == (Coords(row=1, col=1),)
    assert upper.connection.last_used_iteration is None
    assert not upper.has_unexplored_terrain
    assert tuple(connection.source_coords for connection in upper.other_connections) == (
        (Coords(row=1, col=1),),
        (Coords(row=1, col=3),),
    )
    assert result.connection.source_coords == (Coords(row=1, col=1), Coords(row=1, col=2))
    assert result.connection.destination_coords == (Coords(row=3, col=1),)
    assert result.connection.last_used_iteration == warps[MapId.MT_MOON_B1F][2].last_used_iteration
    assert result.has_unexplored_terrain
    assert tuple(connection.source_coords for connection in result.other_connections) == (
        (Coords(row=3, col=1),),
        (Coords(row=3, col=3),),
        (Coords(row=4, col=4),),
    )
    assert tuple(connection.destination_coords for connection in result.other_connections) == (
        (Coords(row=1, col=1), Coords(row=1, col=2)),
        (Coords(row=0, col=0), Coords(row=0, col=1)),
        (Coords(row=2, col=0),),
    )
    assert tuple(connection.destination_map_id for connection in result.other_connections) == (
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
        _boundary(FacingDirection.DOWN, 4, col, destination_map_id).model_copy(
            update={"destination_row": 1, "destination_col": col}
        )
        for col in (1, 3)
    ]
    return_boundary = _boundary(FacingDirection.UP, 1, 1, source_map_id).model_copy(
        update={"map_id": destination_map_id}
    )
    onward_boundary = _boundary(FacingDirection.DOWN, 2, 2, MapId.ROUTE_4).model_copy(
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
        results = await check_connection(
            map_name=source_map_id.name,
            coordinates=Coords(row=4, col=3),
            hm_tiles=[],
        )

    assert isinstance(results, list)
    (result,) = results
    assert not result.connection.is_warp
    assert result.connection.source_coords == (Coords(row=4, col=1), Coords(row=4, col=3))
    assert result.connection.destination_coords == (Coords(row=1, col=1), Coords(row=1, col=3))
    assert not result.has_unexplored_terrain
    assert tuple(connection.destination_map_id for connection in result.other_connections) == (
        None,
        MapId.ROUTE_4,
        source_map_id,
        MapId.ROUTE_4,
    )
    assert tuple(connection.destination_coords for connection in result.other_connections) == (
        (),
        (),
        (Coords(row=0, col=0),),
        (Coords(row=7, col=8),),
    )
    assert tuple(connection.is_warp for connection in result.other_connections) == (
        True,
        True,
        False,
        False,
    )


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
        results = await check_connection(
            map_name=MapId.ROCKET_HIDEOUT_B1F.name,
            coordinates=Coords(row=1, col=1),
            hm_tiles=[],
        )

    assert isinstance(results, list)
    (result,) = results
    assert result.connection.destination_map_id == MapId.ROCKET_HIDEOUT_ELEVATOR
    # B4F has an incoming route, but no elevator route to B4F has been observed.
    assert tuple(route.destination_map_id for route in result.other_connections) == (
        MapId.ROCKET_HIDEOUT_B1F,
        MapId.ROCKET_HIDEOUT_B2F,
    )
    assert all(
        route.source_coords == (Coords(row=1, col=2), Coords(row=1, col=3))
        for route in result.other_connections
    )


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
    arrival = _warp(0, 1, 1, MapId.ROUTE_4, 2)
    connected = _warp(1, 1, 3, MapId.MT_MOON_B2F, 3)
    disconnected = _warp(2, 3, 3, MapId.MT_MOON_B2F, 1)
    connected_boundaries = [
        _boundary(FacingDirection.UP, row, col, MapId.MT_MOON_1F) for row, col in ((1, 2), (2, 3))
    ]
    disconnected_boundary = _boundary(FacingDirection.DOWN, 3, 2, MapId.MT_MOON_B2F)
    map_memory = MapMemoryRead(
        map_id=MapId.MT_MOON_B1F,
        terrain=f"{top_row}\n▓∙∙∙▓\n▓▓▓▓▓\n▓∙∙∙▓\n▓▓▓▓▓",
        blockages={},
    )

    groups, boundary_groups, has_unexplored_terrain = get_connection_component(
        arrival_coords=Coords(row=arrival.row, col=arrival.col),
        warp_groups=group_remembered_warps([arrival, connected, disconnected]),
        boundaries=[*connected_boundaries, disconnected_boundary],
        map_memory=map_memory,
        hm_tiles=[],
    )

    assert tuple(tuple(warp.warp_id for warp in group) for group in groups) == ((0,), (1,))
    assert tuple(
        tuple((boundary.row, boundary.col) for boundary in group) for group in boundary_groups
    ) == (((1, 2), (2, 3)),)
    assert has_unexplored_terrain is expected_unexplored_terrain


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

    _, _, has_unexplored_terrain = get_connection_component(
        arrival_coords=Coords(row=1, col=1),
        warp_groups=(),
        boundaries=[],
        map_memory=map_memory,
        hm_tiles=[],
    )

    assert has_unexplored_terrain is expected_unexplored_terrain
