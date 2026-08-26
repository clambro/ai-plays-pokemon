"""Domain tests for observed cross-map route recall."""

import pytest

from agent.overworld.tools.recall_route.schemas import RouteSearchState
from agent.overworld.tools.recall_route.service import find_route
from common.enums import AsciiTile, Button, MapId
from common.schemas import Coords
from database.map_memory.schemas import MapMemoryRead
from database.route_memory.schemas import RouteTransitionRead


@pytest.mark.unit
def test_route_recall_chooses_the_nearest_entry_to_a_map() -> None:
    """Prefer a direct known entry over another route to the same destination."""
    through_forest = _transition(MapId.PEWTER_CITY, MapId.VIRIDIAN_FOREST, Button.RIGHT)
    direct = _transition(MapId.PEWTER_CITY, MapId.ROUTE_2, Button.DOWN)
    forest_exit = _transition(MapId.VIRIDIAN_FOREST, MapId.ROUTE_2, Button.DOWN)

    route = find_route(
        search=_search_state(),
        destination_map_id=MapId.ROUTE_2,
        transitions=[through_forest, direct, forest_exit],
        map_memories={},
    )

    assert route == [direct]


@pytest.mark.unit
def test_route_recall_derives_disconnected_regions_from_current_capabilities() -> None:
    """Keep Route 2 divided until Cut makes its two observed transitions reachable."""
    enter_route_2 = _transition(
        MapId.PEWTER_CITY,
        MapId.ROUTE_2,
        Button.DOWN,
        destination_coords=Coords(row=0, col=1),
    )
    leave_route_2 = _transition(
        MapId.ROUTE_2,
        MapId.VIRIDIAN_CITY,
        Button.DOWN,
        source_coords=Coords(row=4, col=1),
    )
    route_2 = MapMemoryRead(
        map_id=MapId.ROUTE_2,
        terrain="▓∙▓\n▓∙▓\n▓†▓\n▓∙▓\n▓∙▓",
        blockages={},
    )
    assert (
        find_route(
            search=_search_state(),
            destination_map_id=MapId.VIRIDIAN_CITY,
            transitions=[enter_route_2, leave_route_2],
            map_memories={MapId.ROUTE_2: route_2},
        )
        is None
    )
    assert find_route(
        search=_search_state(hm_tiles=[AsciiTile.CUT_TREE]),
        destination_map_id=MapId.VIRIDIAN_CITY,
        transitions=[enter_route_2, leave_route_2],
        map_memories={MapId.ROUTE_2: route_2},
    ) == [
        enter_route_2,
        leave_route_2,
    ]


def _transition(
    source_map_id: MapId,
    destination_map_id: MapId,
    button: Button,
    *,
    source_coords: Coords | None = None,
    destination_coords: Coords | None = None,
) -> RouteTransitionRead:
    """Build one observed route fact for a domain test."""
    default_coords = Coords(row=1, col=1)
    return RouteTransitionRead(
        source_map_id=source_map_id,
        source_coords=source_coords or default_coords,
        button=button,
        warp_activation=None,
        destination_map_id=destination_map_id,
        destination_coords=destination_coords or default_coords,
        create_iteration=1,
    )


def _search_state(*, hm_tiles: list[AsciiTile] | None = None) -> RouteSearchState:
    """Build the current route-search state for a domain test."""
    coords = Coords(row=1, col=1)
    return RouteSearchState(
        map_id=MapId.PEWTER_CITY,
        coords=coords,
        reachable_coords=frozenset({coords}),
        hm_tiles=hm_tiles or [],
        visited_map_ids=frozenset({MapId.PEWTER_CITY}),
    )
