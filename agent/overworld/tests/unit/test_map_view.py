"""Tests for the derived current-map view."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from agent.overworld import navigation
from agent.overworld.formatting import format_sprite_notes
from agent.overworld.map_view import build_current_map_view
from common.enums import AsciiTile, Button, FacingDirection, MapId, WarpActivation
from common.schemas import Coords
from emulator.parsers.sprite import Sprite
from emulator.parsers.warp import Warp
from overworld_map.schemas import OverworldMap

if TYPE_CHECKING:
    from emulator.game_state import GameState


@pytest.mark.unit
def test_current_map_view_crops_region_without_mutating_map() -> None:
    """The display is a rectangular global-coordinate crop around the current region."""
    overworld_map = OverworldMap(
        id=MapId.ROUTE_2,
        terrain=[
            list("▓▓▓▓▓▓▓"),
            list("▓∙▓▓▓▓▓"),
            list("▓▓∙∙▓∙▓"),
            list("▓▓∙∙▓∙▓"),
            list("▓▓▓▓∙▓▓"),
        ],
        blockages={},
        known_sprite_ids=set(),
        sprite_interactions={},
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids=set(),
        object_interactions={},
        known_warp_ids=set(),
        warp_usage_iterations={},
        known_map_boundaries=(),
        known_map_ids=frozenset(),
        north_connection=None,
        south_connection=None,
        east_connection=None,
        west_connection=None,
    )
    game_state = cast(
        "GameState",
        SimpleNamespace(
            sprites={},
            warps={},
            signs={},
            objects={},
            pikachu=SimpleNamespace(is_rendered=False),
            player=SimpleNamespace(coords=Coords(row=2, col=2), is_surfing=False),
            map=SimpleNamespace(),
            get_hm_tiles=list,
        ),
    )

    map_view = build_current_map_view(overworld_map, game_state)

    assert map_view.display_tiles.tolist() == [
        [
            AsciiTile.OUTSIDE_REGION,
            AsciiTile.WALL,
            AsciiTile.WALL,
            AsciiTile.WALL,
        ],
        [
            AsciiTile.WALL,
            AsciiTile.PLAYER,
            AsciiTile.FREE,
            AsciiTile.WALL,
        ],
        [
            AsciiTile.WALL,
            AsciiTile.FREE,
            AsciiTile.FREE,
            AsciiTile.WALL,
        ],
        [
            AsciiTile.WALL,
            AsciiTile.WALL,
            AsciiTile.WALL,
            AsciiTile.OUTSIDE_REGION,
        ],
    ]
    assert map_view.display_origin == Coords(row=1, col=1)
    assert map_view.reachable_coords == frozenset(
        {
            Coords(row=2, col=2),
            Coords(row=2, col=3),
            Coords(row=3, col=2),
            Coords(row=3, col=3),
        },
    )
    assert overworld_map.terrain == [
        list("▓▓▓▓▓▓▓"),
        list("▓∙▓▓▓▓▓"),
        list("▓▓∙∙▓∙▓"),
        list("▓▓∙∙▓∙▓"),
        list("▓▓▓▓∙▓▓"),
    ]


@pytest.mark.unit
def test_object_overlay_provides_reachable_interaction_position() -> None:
    """Compose a known object over terrain and derive how to interact with it."""
    overworld_map = OverworldMap(
        id=MapId.BILLS_HOUSE,
        terrain=[
            list("▓▓▓▓▓"),
            list("▓∙∙∙▓"),
            list("▓∙∙∙▓"),
            list("▓∙∙∙▓"),
            list("▓▓▓▓▓"),
        ],
        blockages={},
        known_sprite_ids=set(),
        sprite_interactions={},
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids={0},
        object_interactions={},
        known_warp_ids=set(),
        warp_usage_iterations={},
        known_map_boundaries=(),
        known_map_ids=frozenset(),
        north_connection=None,
        south_connection=None,
        east_connection=None,
        west_connection=None,
    )
    game_state = cast(
        "GameState",
        SimpleNamespace(
            sprites={},
            warps={},
            signs={},
            objects={
                0: SimpleNamespace(
                    index=0,
                    coords=Coords(row=1, col=2),
                    interaction_direction=FacingDirection.UP,
                )
            },
            pikachu=SimpleNamespace(is_rendered=False),
            player=SimpleNamespace(coords=Coords(row=2, col=2), is_surfing=False),
            map=SimpleNamespace(),
            get_hm_tiles=list,
        ),
    )

    map_view = build_current_map_view(overworld_map, game_state)

    assert map_view.routing_tiles[1, 2] == AsciiTile.OBJECT
    assert len(map_view.object_interaction_positions[0]) == 1
    assert map_view.object_interaction_positions[0][0].coords == Coords(row=2, col=2)
    assert map_view.object_interaction_positions[0][0].direction == FacingDirection.UP
    assert overworld_map.terrain[1][2] == AsciiTile.FREE


@pytest.mark.unit
def test_spinner_routing_uses_terrain_under_pikachu_overlay() -> None:
    """Resolve spinner paths from terrain even when Pikachu covers the stop tile."""
    overworld_map = OverworldMap(
        id=MapId.ROCKET_HIDEOUT_B3F,
        terrain=[
            list("▓▓▓▓▓"),
            list("▓∙›∙●"),  # noqa: RUF001
            list("▓∙∙∙▓"),
            list("▓▓▓▓▓"),
        ],
        blockages={},
        known_sprite_ids=set(),
        sprite_interactions={},
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids=set(),
        object_interactions={},
        known_warp_ids=set(),
        warp_usage_iterations={},
        known_map_boundaries=(),
        known_map_ids=frozenset(),
        north_connection=None,
        south_connection=None,
        east_connection=None,
        west_connection=None,
    )
    spinner_stop = Coords(row=1, col=4)
    game_state = cast(
        "GameState",
        SimpleNamespace(
            sprites={},
            warps={},
            signs={},
            objects={},
            pikachu=SimpleNamespace(is_rendered=True, coords=spinner_stop),
            player=SimpleNamespace(coords=Coords(row=2, col=2), is_surfing=False),
            map=SimpleNamespace(),
            get_hm_tiles=list,
        ),
    )

    map_view = build_current_map_view(overworld_map, game_state)

    display_row = spinner_stop.row - map_view.display_origin.row
    display_col = spinner_stop.col - map_view.display_origin.col
    assert map_view.routing_tiles[spinner_stop.row, spinner_stop.col] == AsciiTile.SPINNER_STOP
    assert map_view.display_tiles[display_row, display_col] == AsciiTile.PIKACHU
    assert overworld_map.terrain[spinner_stop.row][spinner_stop.col] == AsciiTile.SPINNER_STOP
    assert spinner_stop in map_view.reachable_coords


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tile", "player_row", "expected_path"),
    [
        (AsciiTile.FREE, 3, [Button.UP, Button.UP]),
        (AsciiTile.WARP, 3, [Button.LEFT, Button.UP, Button.UP, Button.RIGHT]),
        (AsciiTile.BOULDER_HOLE, 3, [Button.LEFT, Button.UP, Button.UP, Button.RIGHT]),
        (AsciiTile.WARP, 2, [Button.UP]),
        (AsciiTile.BOULDER_HOLE, 2, [Button.UP]),
    ],
)
def test_routing_respects_tiles_beneath_player_and_pikachu(
    tile: AsciiTile, player_row: int, expected_path: list[Button]
) -> None:
    """Route around transitions beneath Pikachu, but allow leaving the player's starting tile."""
    transition = Coords(row=2, col=2)
    start = Coords(row=player_row, col=2)
    target = Coords(row=1, col=2)
    warps = (
        {
            0: Warp(
                index=0,
                coords=transition,
                destination=MapId.ROCKET_HIDEOUT_B4F,
                destination_warp_index=0,
                destination_coords=Coords(row=10, col=19),
                activation=WarpActivation.STEP_ON,
            )
        }
        if tile == AsciiTile.WARP
        else {}
    )
    terrain_tile = AsciiTile.FREE if tile == AsciiTile.WARP else tile
    overworld_map = OverworldMap(
        id=MapId.ROCKET_HIDEOUT_B3F,
        terrain=[
            list("▓▓▓▓▓"),
            list("▓∙∙∙▓"),
            list(f"▓∙{terrain_tile}▓▓"),
            list("▓∙∙▓▓"),
            list("▓▓▓▓▓"),
        ],
        blockages={},
        known_sprite_ids=set(),
        sprite_interactions={},
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids=set(),
        object_interactions={},
        known_warp_ids=set(warps),
        warp_usage_iterations={},
        known_map_boundaries=(),
        known_map_ids=frozenset(),
        north_connection=None,
        south_connection=None,
        east_connection=None,
        west_connection=None,
    )
    game_state = cast(
        "GameState",
        SimpleNamespace(
            sprites={},
            warps=warps,
            signs={},
            objects={},
            pikachu=Sprite(
                index=15,
                label="PIKACHU",
                coords=transition if start != transition else Coords(row=3, col=2),
                is_rendered=True,
                moves_randomly=False,
            ),
            player=SimpleNamespace(coords=start, is_surfing=False),
            map=SimpleNamespace(),
            get_hm_tiles=list,
        ),
    )

    map_view = build_current_map_view(overworld_map, game_state)
    path = navigation.calculate_path_to_target(
        start, target, map_view.routing_tiles, overworld_map.blockages, []
    )

    assert path == expected_path
    assert target in map_view.reachable_coords
    if start != transition:
        assert navigation.calculate_path_to_target(
            start, transition, map_view.routing_tiles, overworld_map.blockages, []
        ) == [Button.UP]


@pytest.mark.unit
def test_unresolved_spinner_shows_known_path_without_exposing_disconnected_terrain() -> None:
    """Show a spinner's revealed turns and unknown frontier without assuming its destination."""
    overworld_map = OverworldMap(
        id=MapId.ROCKET_HIDEOUT_B3F,
        terrain=[
            list("▓▓▓▓▓▓▓"),
            list("▓∙›∙∨▓▓"),  # noqa: RUF001
            list("▓▓▓▓∙▓▓"),
            list("▓▓▓▓░▓▓"),
            list("▓▓▓▓●▓▓"),
            list("▓▓▓▓▓▓▓"),
        ],
        blockages={},
        known_sprite_ids=set(),
        sprite_interactions={},
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids=set(),
        object_interactions={},
        known_warp_ids=set(),
        warp_usage_iterations={},
        known_map_boundaries=(),
        known_map_ids=frozenset(),
        north_connection=None,
        south_connection=None,
        east_connection=None,
        west_connection=None,
    )
    start = Coords(row=1, col=1)
    entry = Coords(row=1, col=2)
    game_state = cast(
        "GameState",
        SimpleNamespace(
            sprites={},
            warps={},
            signs={},
            objects={},
            pikachu=SimpleNamespace(is_rendered=False),
            player=SimpleNamespace(coords=start, is_surfing=False),
            map=SimpleNamespace(),
            get_hm_tiles=list,
        ),
    )

    map_view = build_current_map_view(overworld_map, game_state)

    assert map_view.exploration_candidates == (entry,)
    assert map_view.reachable_coords == frozenset({start, entry})
    for row, col in ((1, 2), (1, 3), (1, 4), (2, 4), (3, 4)):
        assert Coords(row=row, col=col) in map_view.visible_coords
        assert (
            map_view.display_tiles[
                row - map_view.display_origin.row, col - map_view.display_origin.col
            ]
            == overworld_map.terrain[row][col]
        )
    assert Coords(row=4, col=4) not in map_view.visible_coords


@pytest.mark.unit
def test_sprite_notes_include_only_reachable_and_counter_interactable_sprites() -> None:
    """Expose a disconnected sprite only when the ROM permits talking across its counter."""
    overworld_map = OverworldMap(
        id=MapId.VIRIDIAN_POKECENTER,
        terrain=[
            list("▓▓▓▓▓▓▓"),
            list("▓∙▓∙∙∙▓"),
            list("▓∙‡∙∙∙▓"),
            list("▓∙▓∙∙∙▓"),
            list("▓▓▓▓▓▓▓"),
        ],
        blockages={},
        known_sprite_ids={1, 2},
        sprite_interactions={},
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids=set(),
        object_interactions={},
        known_warp_ids=set(),
        warp_usage_iterations={},
        known_map_boundaries=(),
        known_map_ids=frozenset(),
        north_connection=None,
        south_connection=None,
        east_connection=None,
        west_connection=None,
    )
    sprites = {
        1: SimpleNamespace(
            index=1,
            label="NURSE",
            coords=Coords(row=2, col=3),
            moves_randomly=False,
        ),
        2: SimpleNamespace(
            index=2,
            label="POKEMON",
            coords=Coords(row=1, col=4),
            moves_randomly=False,
        ),
    }
    game_state = cast(
        "GameState",
        SimpleNamespace(
            sprites=sprites,
            warps={},
            signs={},
            objects={},
            screen=SimpleNamespace(to_screen_coords=lambda _coords: Coords(row=0, col=0)),
            pikachu=SimpleNamespace(is_rendered=False),
            player=SimpleNamespace(coords=Coords(row=2, col=1), is_surfing=False),
            map=SimpleNamespace(),
            get_hm_tiles=list,
        ),
    )

    map_view = build_current_map_view(overworld_map, game_state)
    notes = format_sprite_notes(map_view, game_state)

    assert map_view.counter_interactions == {1: (Coords(row=2, col=1),)}
    assert "NURSE" in notes
    assert "across a counter from (2, 1)" in notes
    assert "POKEMON" not in notes
