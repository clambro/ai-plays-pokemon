"""Domain tests for remembered connection-component checks."""

import pytest

from agent.overworld.tools.check_connection.service import get_connection_component
from common.enums import FacingDirection, MapId, WarpActivation
from common.schemas import Coords
from database.map_boundary_memory.schemas import MapBoundaryMemoryRead
from database.map_memory.schemas import MapMemoryRead
from database.warp_memory.schemas import WarpMemoryRead


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
        warps=[arrival, connected, disconnected],
        boundaries=[*connected_boundaries, disconnected_boundary],
        map_memory=map_memory,
        hm_tiles=[],
    )

    assert tuple(tuple(warp.warp_id for warp in group) for group in groups) == ((0,), (1,))
    assert tuple(
        tuple((boundary.row, boundary.col) for boundary in group) for group in boundary_groups
    ) == (((1, 2), (2, 3)),)
    assert has_unexplored_terrain is expected_unexplored_terrain
