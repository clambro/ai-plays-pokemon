"""
Tests for the navigation service.

It's a bit of an antipattern to use strings for the maps instead of the enum values because if we
ever need to change the characters used, we'll have to update the tests, but this is far more
readable.
"""

from copy import deepcopy

import pytest

from agent.subflows.overworld_handler.nodes.navigate import utils
from common.enums import BlockedDirection, Button, FacingDirection, MapId
from common.schemas import Coords
from overworld_map.schemas import OverworldMap

PLATEAU_MAP = [
    list(row)
    for row in [
        "▉▉▉▉▉▉▉▉▉▉▉",
        "░∙⍅∙∙∙∙∙⍆∙░",
        "░∙⍅∙∙∙∙∙⍆∙░",
        "░∙⍅∙∙∙∙∙⍆∙∙",
        "░∙▉⍖⍖∙⍖⍖▉∙░",
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

DUMMY_MAP = OverworldMap(
    id=MapId.PALLET_TOWN,
    ascii_tiles=[[]],
    blockages={},
    known_sprites={},
    known_signs={},
    known_warps={},
    north_connection=None,
    south_connection=None,
    east_connection=None,
    west_connection=None,
)


@pytest.mark.unit
async def test_get_accessible_coords_plateau() -> None:
    """Test that the accessible coords are correct for the plateau map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = PLATEAU_MAP

    accessible_coords = await utils.get_accessible_coords(PLATEAU_CENTER, map_data)
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
async def test_get_accessible_coords_collision_pairs() -> None:
    """Test that the accessible coords are correct for the collision pairs map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = COLLISION_PAIRS_MAP
    map_data.blockages = COLLISION_PAIRS_BLOCKAGES

    accessible_coords = await utils.get_accessible_coords(Coords(row=0, col=0), map_data)
    assert _coords_to_binary_map(set(accessible_coords), 3, 3) == [
        "110",
        "011",
        "111",
    ]


@pytest.mark.unit
async def test_get_exploration_candidates_plateau() -> None:
    """Test that the exploration candidates are correct for the plateau map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = PLATEAU_MAP

    accessible_coords = await utils.get_accessible_coords(PLATEAU_CENTER, map_data)
    exploration_candidates = utils.get_exploration_candidates(accessible_coords, map_data)
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
async def test_get_exploration_candidates_collision_pairs() -> None:
    """Test that the exploration candidates are correct for the collision pairs map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = COLLISION_PAIRS_MAP
    map_data.blockages = COLLISION_PAIRS_BLOCKAGES

    accessible_coords = await utils.get_accessible_coords(Coords(row=0, col=0), map_data)
    exploration_candidates = utils.get_exploration_candidates(accessible_coords, map_data)
    assert exploration_candidates == []


@pytest.mark.unit
async def test_get_map_boundary_tiles_plateau() -> None:
    """Test that the map boundary tiles are correct for the plateau map if we add a map below."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = PLATEAU_MAP
    map_data.south_connection = MapId.ROUTE_1

    accessible_coords = await utils.get_accessible_coords(PLATEAU_CENTER, map_data)
    boundary_tiles = utils.get_map_boundary_tiles(accessible_coords, map_data)

    # There is no right boundary tile because the map is not connected to the right.
    assert boundary_tiles == {
        FacingDirection.DOWN: [Coords(row=6, col=5)],
        FacingDirection.LEFT: [],
        FacingDirection.RIGHT: [],
        FacingDirection.UP: [],
    }


@pytest.mark.unit
async def test_get_map_boundary_tiles_collision_pairs() -> None:
    """Test that the map boundary tiles are correct for the collision pairs map."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = COLLISION_PAIRS_MAP
    map_data.blockages = COLLISION_PAIRS_BLOCKAGES
    map_data.east_connection = MapId.ROUTE_1
    map_data.west_connection = MapId.ROUTE_1

    accessible_coords = await utils.get_accessible_coords(Coords(row=0, col=0), map_data)
    boundary_tiles = utils.get_map_boundary_tiles(accessible_coords, map_data)

    assert boundary_tiles[FacingDirection.DOWN] == []
    assert set(boundary_tiles[FacingDirection.LEFT]) == {Coords(row=0, col=0), Coords(row=2, col=0)}
    assert set(boundary_tiles[FacingDirection.RIGHT]) == {
        Coords(row=1, col=2),
        Coords(row=2, col=2),
    }
    assert boundary_tiles[FacingDirection.UP] == []


@pytest.mark.unit
async def test_calculate_path_to_target_plateau_jump_left() -> None:
    """Test that the path to the target is correct for the plateau map when jumping left."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = PLATEAU_MAP

    path = await utils.calculate_path_to_target(PLATEAU_CENTER, Coords(row=2, col=1), map_data)
    assert path == 3 * [Button.LEFT]


@pytest.mark.unit
async def test_calculate_path_to_target_plateau_from_left_around() -> None:
    """
    Test that the path to the target is correct for the plateau map when walking from the left to
    the center.
    """
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = PLATEAU_MAP

    path = await utils.calculate_path_to_target(Coords(row=2, col=1), PLATEAU_CENTER, map_data)
    assert path == 3 * [Button.DOWN] + 4 * [Button.RIGHT] + 3 * [Button.UP]


@pytest.mark.unit
async def test_calculate_path_to_target_plateau_jump_right() -> None:
    """Test that the path to the target is correct for the plateau map when jumping right."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = PLATEAU_MAP

    path = await utils.calculate_path_to_target(PLATEAU_CENTER, Coords(row=2, col=9), map_data)
    assert path == 3 * [Button.RIGHT]


@pytest.mark.unit
async def test_calculate_path_to_target_plateau_from_right_around() -> None:
    """
    Test that the path to the target is correct for the plateau map when walking from the right to
    the center.
    """
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = PLATEAU_MAP

    path = await utils.calculate_path_to_target(Coords(row=2, col=9), PLATEAU_CENTER, map_data)
    assert path == 3 * [Button.DOWN] + 4 * [Button.LEFT] + 3 * [Button.UP]


@pytest.mark.unit
async def test_calculate_path_to_target_plateau_jump_down() -> None:
    """Test that the path to the target is correct for the plateau map when jumping down."""
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = PLATEAU_MAP

    path = await utils.calculate_path_to_target(
        Coords(row=3, col=4),
        Coords(row=5, col=4),
        map_data,
    )
    assert path == [Button.DOWN]


@pytest.mark.unit
async def test_calculate_path_to_target_plateau_from_down_around() -> None:
    """
    Test that the path to the target is correct for the plateau map when walking from the down to
    the center.
    """
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = PLATEAU_MAP

    path = await utils.calculate_path_to_target(
        Coords(row=5, col=4),
        Coords(row=3, col=4),
        map_data,
    )
    assert path == [Button.RIGHT, Button.UP, Button.UP, Button.LEFT]


@pytest.mark.unit
async def test_calculate_path_to_target_around_collision_pair() -> None:
    """
    Test that the path to the target is correct for the collision pairs map when walking around a
    collision pair.
    """
    map_data = deepcopy(DUMMY_MAP)
    map_data.ascii_tiles = COLLISION_PAIRS_MAP
    map_data.blockages = COLLISION_PAIRS_BLOCKAGES

    path = await utils.calculate_path_to_target(
        Coords(row=0, col=0),
        Coords(row=2, col=0),
        map_data,
    )
    assert path == [Button.RIGHT, Button.DOWN, Button.DOWN, Button.LEFT]


def _coords_to_binary_map(coords: set[Coords], height: int, width: int) -> list[str]:
    """Convert a coords to a binary string for more visual matching."""
    return [
        "".join("1" if Coords(row=row, col=col) in coords else "0" for col in range(width))
        for row in range(height)
    ]
