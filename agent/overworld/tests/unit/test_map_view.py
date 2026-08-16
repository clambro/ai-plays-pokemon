"""Tests for the derived current-map view."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from agent.overworld.formatting import format_sprite_notes
from agent.overworld.map_view import build_current_map_view
from common.enums import AsciiTile, MapId
from common.schemas import Coords
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
        known_sign_ids=set(),
        known_warp_ids=set(),
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
        known_sign_ids=set(),
        known_warp_ids=set(),
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
