"""Tests for the derived current-map view."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from agent.overworld.map_view import build_current_map_view
from common.enums import AsciiTile, MapId
from common.schemas import Coords
from overworld_map.schemas import OverworldMap

if TYPE_CHECKING:
    from emulator.game_state import GameState


@pytest.mark.unit
def test_current_map_view_masks_disconnected_terrain_without_mutating_map() -> None:
    """Only the player's navigable region and its immediate boundary are exposed."""
    overworld_map = OverworldMap(
        id=MapId.ROUTE_2,
        terrain=[list("∙∙▓∙∙"), list("∙∙▓∙∙")],
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
            player=SimpleNamespace(coords=Coords(row=0, col=0)),
            get_hm_tiles=list,
        ),
    )

    map_view = build_current_map_view(overworld_map, game_state)

    assert map_view.display_tiles.tolist() == [
        [
            AsciiTile.PLAYER,
            AsciiTile.FREE,
            AsciiTile.WALL,
            AsciiTile.OUTSIDE_REGION,
            AsciiTile.OUTSIDE_REGION,
        ],
        [
            AsciiTile.FREE,
            AsciiTile.FREE,
            AsciiTile.WALL,
            AsciiTile.OUTSIDE_REGION,
            AsciiTile.OUTSIDE_REGION,
        ],
    ]
    assert map_view.reachable_coords == frozenset(
        {
            Coords(row=0, col=0),
            Coords(row=0, col=1),
            Coords(row=1, col=0),
            Coords(row=1, col=1),
        },
    )
    assert overworld_map.terrain == [list("∙∙▓∙∙"), list("∙∙▓∙∙")]
