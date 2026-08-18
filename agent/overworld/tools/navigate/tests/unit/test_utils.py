"""Tests for the navigation service.

It's a bit of an antipattern to use strings for the maps instead of the enum values because if we
ever need to change the characters used, we'll have to update the tests, but this is far more
readable.
"""

from copy import deepcopy

import pytest

from agent.overworld import navigation
from common.enums import AsciiTile, BlockedDirection, Button, FacingDirection, MapId
from common.schemas import Coords
from emulator.parsers.map import Map, MapConnection
from overworld_map.schemas import OverworldMap

PLATEAU_MAP = [
    list(row)
    for row in [
        "▓▓▓▓▓▓▓▓▓▓▓",
        "░∙≤∙∙∙∙∙≥∙░",
        "░∙≤∙∙∙∙∙≥∙░",
        "░∙≤∙∙∙∙∙≥∙∙",
        "░∙▓▽▽∙▽▽▓∙░",
        "░∙∙∙∙∙∙∙∙∙░",
        "░░░░░∙░░░░░",
    ]
]
PLATEAU_CENTER = Coords(row=2, col=5)

COLLISION_PAIRS_MAP = [
    list(row)
    for row in [
        "∙∙∙",  # Position 2 in this row is inaccessible.
        "∙∙∙",  # Position 0 in this row is inaccessible.
        "∙∙∙",  # All positions in this row are accessible.
    ]
]
COLLISION_PAIRS_BLOCKAGES = {
    Coords(row=0, col=0): BlockedDirection.DOWN,
    Coords(row=0, col=1): BlockedDirection.RIGHT,
    Coords(row=0, col=2): BlockedDirection.LEFT | BlockedDirection.DOWN,
    Coords(row=1, col=0): BlockedDirection.UP | BlockedDirection.RIGHT | BlockedDirection.DOWN,
    Coords(row=1, col=1): BlockedDirection.LEFT,
    Coords(row=1, col=2): BlockedDirection.UP,
    Coords(row=2, col=0): BlockedDirection.UP,
}

CUT_TREE_MAP = [list("∙†∙")]

SURF_MAP = [list("∙≈∙")]

SPINNER_MAP = [
    list(row)
    for row in [
        "∙∙▓\u2228∙",
        "\u2228▓∙\u2228\u2039",
        "∙∙∙░░",
        "∙●\u2039░∙",
        "\u203a∙Λ∙∙",
        "∙▓∙∙∙",
    ]
]

DUMMY_MAP = OverworldMap(
    id=MapId.PALLET_TOWN,
    terrain=[[]],
    blockages={},
    known_sprite_ids=set(),
    sprite_interactions={},
    known_sign_ids=set(),
    sign_interactions={},
    known_object_ids=set(),
    object_interactions={},
    known_warp_ids=set(),
    warp_usage_iterations={},
    known_map_ids=frozenset(),
    north_connection=None,
    south_connection=None,
    east_connection=None,
    west_connection=None,
)

DUMMY_MAP_STATE = Map(
    id=MapId.PALLET_TOWN,
    height=1,
    width=1,
    grass_tile=None,
    water_tiles=frozenset({3}),
    talk_over_tiles=frozenset(),
    ledge_tiles_left=[],
    ledge_tiles_right=[],
    ledge_tiles_down=[],
    spinner_tiles=None,
    cut_tree_tiles=None,
    boulder_hole_tiles=None,
    pressure_plate_tiles=None,
    walkable_tiles=[1, 4],
    collision_pairs=[],
    boulder_blocked_tiles=frozenset(),
    north_connection=None,
    south_connection=None,
    east_connection=None,
    west_connection=None,
)


@pytest.mark.unit
def test_get_accessible_coords_plateau() -> None:
    """Test that the accessible coords are correct for the plateau map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = PLATEAU_MAP

    accessible_coords = _get_accessible_coords(PLATEAU_CENTER, map_data, [])
    assert _coords_to_binary_map(set(accessible_coords), 7, 11) == [
        "00000000000",
        "01011111010",
        "01011111010",
        "01011111011",
        "01000100010",
        "01111111110",
        "00000100000",
    ]


@pytest.mark.unit
def test_get_accessible_coords_collision_pairs() -> None:
    """Test that the accessible coords are correct for the collision pairs map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = COLLISION_PAIRS_MAP
    map_data.blockages = COLLISION_PAIRS_BLOCKAGES

    accessible_coords = _get_accessible_coords(Coords(row=0, col=0), map_data, [])
    assert _coords_to_binary_map(set(accessible_coords), 3, 3) == [
        "110",
        "011",
        "111",
    ]


@pytest.mark.unit
def test_get_accessible_coords_cut_tree_no_hm() -> None:
    """Test that the accessible coords are correct for the cut tree map with no HMs."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = CUT_TREE_MAP

    accessible_coords = _get_accessible_coords(Coords(row=0, col=0), map_data, [])
    assert _coords_to_binary_map(set(accessible_coords), 1, 3) == ["100"]


@pytest.mark.unit
def test_get_accessible_coords_cut_tree_with_hm() -> None:
    """Test that the accessible coords are correct for the cut tree map with an HM."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = CUT_TREE_MAP

    accessible_coords = _get_accessible_coords(
        Coords(row=0, col=0),
        map_data,
        [AsciiTile.CUT_TREE],
    )
    assert _coords_to_binary_map(set(accessible_coords), 1, 3) == ["111"]


@pytest.mark.unit
def test_get_accessible_coords_surf_no_hm() -> None:
    """Test that the accessible coords are correct for the surf map with no HMs."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = SURF_MAP

    accessible_coords = _get_accessible_coords(Coords(row=0, col=0), map_data, [])
    assert _coords_to_binary_map(set(accessible_coords), 1, 3) == ["100"]


@pytest.mark.unit
def test_get_accessible_coords_surf_with_hm() -> None:
    """Test that the accessible coords are correct for the surf map with an HM."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = SURF_MAP

    accessible_coords = _get_accessible_coords(
        Coords(row=0, col=0),
        map_data,
        [AsciiTile.WATER],
    )
    assert _coords_to_binary_map(set(accessible_coords), 1, 3) == ["111"]


@pytest.mark.unit
def test_get_accessible_coords_spinner() -> None:
    """Test that the accessible coords are correct for the spinner map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = SPINNER_MAP

    accessible_coords = _get_accessible_coords(Coords(row=0, col=0), map_data, [])
    assert _coords_to_binary_map(set(accessible_coords), 6, 5) == [
        "11000",
        "00110",
        "11100",
        "11000",
        "01000",
        "00000",
    ]


@pytest.mark.unit
def test_get_exploration_candidates_plateau() -> None:
    """Test that the exploration candidates are correct for the plateau map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = PLATEAU_MAP

    accessible_coords = _get_accessible_coords(PLATEAU_CENTER, map_data, [])
    exploration_candidates = _get_exploration_candidates(accessible_coords, map_data)
    assert _coords_to_binary_map(set(exploration_candidates), 7, 11) == [
        "00000000000",
        "01000000010",
        "01000000010",
        "01000000001",
        "01000000010",
        "01111011110",
        "00000100000",
    ]


@pytest.mark.unit
def test_get_exploration_candidates_collision_pairs() -> None:
    """Test that the exploration candidates are correct for the collision pairs map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = COLLISION_PAIRS_MAP
    map_data.blockages = COLLISION_PAIRS_BLOCKAGES

    accessible_coords = _get_accessible_coords(Coords(row=0, col=0), map_data, [])
    exploration_candidates = _get_exploration_candidates(accessible_coords, map_data)
    assert exploration_candidates == []


@pytest.mark.unit
def test_get_map_boundary_tiles_plateau() -> None:
    """Test that the map boundary tiles are correct for the plateau map if we add a map below."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = PLATEAU_MAP
    map_data.south_connection = MapConnection(
        direction=FacingDirection.DOWN,
        destination_map=MapId.ROUTE_1,
        source_coordinate_start=0,
        source_coordinate_end=len(PLATEAU_MAP[0]),
        destination_offset=Coords(row=0, col=0),
        collision_tile_pairs=((1, 1),) * len(PLATEAU_MAP[0]),
    )

    accessible_coords = _get_accessible_coords(PLATEAU_CENTER, map_data, [])
    boundary_tiles = _get_map_boundary_tiles(accessible_coords, map_data)

    # There is no right boundary tile because the map is not connected to the right.
    assert boundary_tiles == {
        FacingDirection.DOWN: [Coords(row=6, col=5)],
        FacingDirection.LEFT: [],
        FacingDirection.RIGHT: [],
        FacingDirection.UP: [],
    }


@pytest.mark.unit
def test_get_map_boundary_tiles_collision_pairs() -> None:
    """Test that the map boundary tiles are correct for the collision pairs map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = COLLISION_PAIRS_MAP
    map_data.blockages = COLLISION_PAIRS_BLOCKAGES
    map_data.east_connection = MapConnection(
        direction=FacingDirection.RIGHT,
        destination_map=MapId.ROUTE_1,
        source_coordinate_start=0,
        source_coordinate_end=len(COLLISION_PAIRS_MAP),
        destination_offset=Coords(row=0, col=0),
        collision_tile_pairs=((1, 1),) * len(COLLISION_PAIRS_MAP),
    )
    map_data.west_connection = MapConnection(
        direction=FacingDirection.LEFT,
        destination_map=MapId.ROUTE_1,
        source_coordinate_start=0,
        source_coordinate_end=len(COLLISION_PAIRS_MAP),
        destination_offset=Coords(row=0, col=0),
        collision_tile_pairs=((1, 1),) * len(COLLISION_PAIRS_MAP),
    )

    accessible_coords = _get_accessible_coords(Coords(row=0, col=0), map_data, [])
    boundary_tiles = _get_map_boundary_tiles(accessible_coords, map_data)

    assert boundary_tiles[FacingDirection.DOWN] == []
    assert set(boundary_tiles[FacingDirection.LEFT]) == {Coords(row=0, col=0), Coords(row=2, col=0)}
    assert set(boundary_tiles[FacingDirection.RIGHT]) == {
        Coords(row=1, col=2),
        Coords(row=2, col=2),
    }
    assert boundary_tiles[FacingDirection.UP] == []


@pytest.mark.unit
def test_get_map_boundary_tiles_checks_connected_map_collision_strip() -> None:
    """Expose only outward tiles that are traversable, even when they are outside the viewport."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = [list("∙∙∙")]
    map_data.south_connection = MapConnection(
        direction=FacingDirection.DOWN,
        destination_map=MapId.ROUTE_1,
        source_coordinate_start=0,
        source_coordinate_end=3,
        destination_offset=Coords(row=0, col=0),
        collision_tile_pairs=(
            (1, 2),  # The connected-map tile is a wall.
            (1, 1),  # The connected-map tile is ordinary walkable terrain.
            (1, 3),  # The connected-map tile is water.
        ),
    )
    accessible_coords = _get_accessible_coords(Coords(row=0, col=0), map_data, [])

    without_surf = _get_map_boundary_tiles(accessible_coords, map_data)
    with_surf = _get_map_boundary_tiles(accessible_coords, map_data, can_surf=True)

    assert without_surf[FacingDirection.DOWN] == [Coords(row=0, col=1)]
    assert with_surf[FacingDirection.DOWN] == [
        Coords(row=0, col=1),
        Coords(row=0, col=2),
    ]


@pytest.mark.unit
def test_get_map_boundary_tiles_checks_cross_boundary_collision_pair() -> None:
    """Reject an otherwise walkable connected-map tile across an elevation boundary."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = [list("∙")]
    map_data.south_connection = MapConnection(
        direction=FacingDirection.DOWN,
        destination_map=MapId.ROUTE_1,
        source_coordinate_start=0,
        source_coordinate_end=1,
        destination_offset=Coords(row=0, col=0),
        collision_tile_pairs=((1, 4),),
    )
    map_state = DUMMY_MAP_STATE.model_copy(
        update={"collision_pairs": [frozenset((1, 4))]},
    )

    boundary_tiles = _get_map_boundary_tiles(
        [Coords(row=0, col=0)],
        map_data,
        map_state=map_state,
    )

    assert boundary_tiles[FacingDirection.DOWN] == []


@pytest.mark.unit
def test_calculate_path_to_target_plateau_jump_left() -> None:
    """Test that the path to the target is correct for the plateau map when jumping left."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = PLATEAU_MAP

    path = _calculate_path_to_target(PLATEAU_CENTER, Coords(row=2, col=1), map_data, [])
    assert path == 3 * [Button.LEFT]


@pytest.mark.unit
def test_calculate_path_to_target_plateau_from_left_around() -> None:
    """Test the path from the plateau's left side to its center."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = PLATEAU_MAP

    path = _calculate_path_to_target(Coords(row=2, col=1), PLATEAU_CENTER, map_data, [])
    assert path == 3 * [Button.DOWN] + 4 * [Button.RIGHT] + 3 * [Button.UP]


@pytest.mark.unit
def test_calculate_path_to_target_plateau_jump_right() -> None:
    """Test that the path to the target is correct for the plateau map when jumping right."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = PLATEAU_MAP

    path = _calculate_path_to_target(PLATEAU_CENTER, Coords(row=2, col=9), map_data, [])
    assert path == 3 * [Button.RIGHT]


@pytest.mark.unit
def test_calculate_path_to_target_plateau_from_right_around() -> None:
    """Test the path from the plateau's right side to its center."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = PLATEAU_MAP

    path = _calculate_path_to_target(Coords(row=2, col=9), PLATEAU_CENTER, map_data, [])
    assert path == 3 * [Button.DOWN] + 4 * [Button.LEFT] + 3 * [Button.UP]


@pytest.mark.unit
def test_calculate_path_to_target_plateau_jump_down() -> None:
    """Test that the path to the target is correct for the plateau map when jumping down."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = PLATEAU_MAP

    path = _calculate_path_to_target(
        Coords(row=3, col=4),
        Coords(row=5, col=4),
        map_data,
        [],
    )
    assert path == [Button.DOWN]


@pytest.mark.unit
def test_calculate_path_to_target_plateau_from_down_around() -> None:
    """Test the path from below the plateau to its center."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = PLATEAU_MAP

    path = _calculate_path_to_target(
        Coords(row=5, col=4),
        Coords(row=3, col=4),
        map_data,
        [],
    )
    assert path == [Button.RIGHT, Button.UP, Button.UP, Button.LEFT]


@pytest.mark.unit
def test_calculate_path_to_target_around_collision_pair() -> None:
    """Test pathfinding around a paired-tile collision."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = COLLISION_PAIRS_MAP
    map_data.blockages = COLLISION_PAIRS_BLOCKAGES

    path = _calculate_path_to_target(
        Coords(row=0, col=0),
        Coords(row=2, col=0),
        map_data,
        [],
    )
    assert path == [Button.RIGHT, Button.DOWN, Button.DOWN, Button.LEFT]


@pytest.mark.unit
def test_calculate_path_around_grass() -> None:
    """Test that the pathing properly avoids the grass tile, even though it's not optimal."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = [
        list(row)
        for row in [
            "∙※∙",
            "∙∙∙",
        ]
    ]

    path = _calculate_path_to_target(
        Coords(row=0, col=0),
        Coords(row=0, col=2),
        map_data,
        [],
    )
    assert path == [Button.DOWN, Button.RIGHT, Button.RIGHT, Button.UP]


@pytest.mark.unit
def test_calculate_path_through_grass() -> None:
    """Test that pathfinding uses grass when it is the only route."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = [
        list(row)
        for row in [
            "∙※∙",
            "∙※∙",
        ]
    ]

    path = _calculate_path_to_target(
        Coords(row=0, col=0),
        Coords(row=0, col=2),
        map_data,
        [],
    )
    assert path == [Button.RIGHT, Button.RIGHT]


@pytest.mark.unit
def test_calculate_path_through_cut_tree() -> None:
    """Test that we can path through a cut tree if we have the right HMs."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = CUT_TREE_MAP

    path = _calculate_path_to_target(
        Coords(row=0, col=0),
        Coords(row=0, col=2),
        map_data,
        [AsciiTile.CUT_TREE],
    )
    assert path == [Button.RIGHT, Button.RIGHT]


@pytest.mark.unit
def test_calculate_path_through_water() -> None:
    """Test that we can path through water if we have the right HMs."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = SURF_MAP

    path = _calculate_path_to_target(
        Coords(row=0, col=0),
        Coords(row=0, col=2),
        map_data,
        [AsciiTile.WATER],
    )
    assert path == [Button.RIGHT, Button.RIGHT]


@pytest.mark.unit
def test_calculate_path_through_spinners() -> None:
    """Test that we can path through spinners."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.terrain = SPINNER_MAP

    path = _calculate_path_to_target(
        Coords(row=0, col=0),
        Coords(row=3, col=1),
        map_data,
        [],
    )
    assert path == [Button.DOWN]


def _coords_to_binary_map(coords: set[Coords], height: int, width: int) -> list[str]:
    """Convert a coords to a binary string for more visual matching."""
    return [
        "".join("1" if Coords(row=row, col=col) in coords else "0" for col in range(width))
        for row in range(height)
    ]


def _get_accessible_coords(
    start_pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[Coords]:
    return navigation.get_accessible_coords(
        start_pos,
        map_data.terrain_ndarray,
        map_data.blockages,
        hm_tiles,
    )


def _get_exploration_candidates(
    accessible_coords: list[Coords],
    map_data: OverworldMap,
) -> list[Coords]:
    return navigation.get_exploration_candidates(accessible_coords, map_data.terrain_ndarray)


def _get_map_boundary_tiles(
    accessible_coords: list[Coords],
    map_data: OverworldMap,
    *,
    map_state: Map = DUMMY_MAP_STATE,
    can_surf: bool = False,
) -> dict[FacingDirection, list[Coords]]:
    return navigation.get_map_boundary_tiles(
        accessible_coords,
        map_data,
        map_state,
        can_surf=can_surf,
    )


def _calculate_path_to_target(
    start_pos: Coords,
    target_pos: Coords,
    map_data: OverworldMap,
    hm_tiles: list[AsciiTile],
) -> list[Button] | None:
    return navigation.calculate_path_to_target(
        start_pos,
        target_pos,
        map_data.terrain_ndarray,
        map_data.blockages,
        hm_tiles,
    )
