"""Tests for explored-map behavior."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from common.enums import (
    AsciiTile,
    Button,
    FacingDirection,
    MapEntityType,
    MapId,
    SpriteLabel,
    WarpActivation,
)
from common.schemas import Coords
from database.map_entity_memory.schemas import MapEntityMemoryRead
from database.map_memory.schemas import MapMemoryRead
from database.warp_memory.schemas import WarpMemoryRead
from emulator.control_events import ControlBoundary, ControlResult
from emulator.parsers.map import MapConnection
from overworld_map.schemas import OverworldMap, TraversalRules
from overworld_map.service import (
    get_overworld_map,
    record_observed_hole_connection,
    record_observed_map_boundary,
    update_overworld_map,
)
from overworld_map.tiles import get_composed_map_tiles, get_navigation_tiles
from overworld_map.traversal import get_accessible_coords

if TYPE_CHECKING:
    from emulator.game_state import GameState

_MAP_STATE = SimpleNamespace(
    id=MapId.PALLET_TOWN,
    north_connection=None,
    south_connection=None,
    east_connection=None,
    west_connection=None,
)


@pytest.mark.unit
@pytest.mark.parametrize("interaction_text", ["Previously observed text.", None])
async def test_load_preserves_discovered_ids_without_live_records(
    interaction_text: str | None,
) -> None:
    """Persisted discoveries and interactions survive even without live records or dialog."""
    interaction_iteration = 7
    memories = [
        MapEntityMemoryRead(
            map_id=MapId.PALLET_TOWN,
            entity_id=entity_id,
            entity_type=entity_type,
            last_interaction=interaction_text,
            last_interaction_iteration=interaction_iteration,
        )
        for entity_id, entity_type in (
            (2, MapEntityType.SPRITE),
            (3, MapEntityType.SIGN),
            (4, MapEntityType.OBJECT),
            (5, MapEntityType.LOCKED_DOOR),
        )
    ]
    warp_memory = WarpMemoryRead(
        map_id=MapId.PALLET_TOWN,
        warp_id=1,
        row=6,
        col=5,
        destination_map_id=MapId.MY_HOUSE_1F,
        destination_warp_id=0,
        activation=WarpActivation.UP,
        last_used_iteration=interaction_iteration,
    )
    game_state = cast("GameState", SimpleNamespace(map=_MAP_STATE, warps={}))

    with patch.multiple(
        "overworld_map.service",
        get_map_memory=AsyncMock(
            return_value=MapMemoryRead(
                map_id=MapId.PALLET_TOWN,
                terrain="∙",
                blockages={},
            ),
        ),
        get_map_entity_memories_for_map=AsyncMock(return_value=memories),
        get_warp_memories_for_map=AsyncMock(return_value=[warp_memory]),
        get_map_boundary_memories_for_map=AsyncMock(return_value=[]),
        get_visited_maps=AsyncMock(return_value=[MapId.PALLET_TOWN]),
    ):
        current_map = await get_overworld_map(1, game_state)

    assert current_map.known_warp_ids == {1}
    assert current_map.warp_usage_iterations == {}
    assert current_map.known_sprite_ids == {2}
    assert current_map.known_sign_ids == {3}
    assert current_map.known_object_ids == {4}
    assert current_map.sprite_interactions[2].text == interaction_text
    assert current_map.sprite_interactions[2].iteration == interaction_iteration
    assert current_map.sign_interactions[3].text == interaction_text
    assert current_map.sign_interactions[3].iteration == interaction_iteration
    assert current_map.object_interactions[4].text == interaction_text
    assert current_map.object_interactions[4].iteration == interaction_iteration
    assert current_map.locked_door_interactions[5].text == interaction_text
    assert current_map.locked_door_interactions[5].iteration == interaction_iteration


@pytest.mark.unit
async def test_update_discovers_present_entities_on_revealed_terrain() -> None:
    """Offscreen arrivals are discovered while hidden entities and their history stay separate."""
    warp = SimpleNamespace(
        index=4,
        coords=Coords(row=2, col=3),
        destination=MapId.MY_HOUSE_1F,
        destination_warp_index=0,
        activation=WarpActivation.UP,
    )
    game_state = MagicMock()
    game_state.map = _MAP_STATE
    game_state.sprites = {
        3: SimpleNamespace(index=3, coords=Coords(row=2, col=2), is_rendered=False),
        8: SimpleNamespace(index=8, coords=Coords(row=0, col=0)),
    }
    game_state.signs = {5: SimpleNamespace(index=5, coords=Coords(row=2, col=2))}
    game_state.objects = {6: SimpleNamespace(index=6, coords=Coords(row=2, col=2))}
    game_state.screen.to_screen_coords.return_value = Coords(row=3, col=3)
    game_state.is_text_on_screen.return_value = False
    game_state.warps = {warp.index: warp}
    current_map = cast(
        "OverworldMap",
        SimpleNamespace(
            id=MapId.PALLET_TOWN,
            height=4,
            width=4,
            terrain=[list("░∙∙∙"), list("∙∙∙∙"), list("∙∙∙∙"), list("∙∙∙∙")],
            known_sprite_ids={1, 2},
            sprite_interactions={2: SimpleNamespace()},
            known_warp_ids=set(),
            known_sign_ids=set(),
            known_object_ids=set(),
        ),
    )

    with (
        patch(
            "overworld_map.service.create_map_entity_memories",
            new_callable=AsyncMock,
        ) as apply_changes,
        patch(
            "overworld_map.service._update_overworld_map_terrain",
            new_callable=AsyncMock,
        ),
        patch(
            "overworld_map.service.remember_warps",
            new_callable=AsyncMock,
        ),
    ):
        await update_overworld_map(1, cast("GameState", game_state), current_map)

    assert current_map.known_sprite_ids == {1, 2, 3}
    assert set(current_map.sprite_interactions) == {2}
    assert current_map.known_warp_ids == {4}
    assert current_map.known_sign_ids == {5}
    assert current_map.known_object_ids == {6}
    assert apply_changes.await_args is not None
    creates = apply_changes.await_args.args[0]
    assert {(change.entity_type, change.entity_id) for change in creates} == {
        (MapEntityType.SPRITE, 3),
        (MapEntityType.SIGN, 5),
        (MapEntityType.OBJECT, 6),
    }


@pytest.mark.unit
async def test_discovered_offscreen_warp_replaces_stale_wall_in_navigation() -> None:
    """A live warp on mapped terrain is usable without revealing unseen or inactive warps."""
    warps = {
        index: SimpleNamespace(
            index=index,
            coords=coords,
            destination=MapId.MY_HOUSE_1F,
            destination_warp_index=0,
            activation=WarpActivation.STEP_ON,
        )
        for index, coords in {
            1: Coords(row=1, col=1),
            2: Coords(row=0, col=0),
        }.items()
    }
    game_state = MagicMock()
    game_state.map = _MAP_STATE
    game_state.warps = warps
    game_state.sprites = {}
    game_state.signs = {}
    game_state.objects = {}
    game_state.is_text_on_screen.return_value = False
    current_map = OverworldMap(
        id=MapId.PALLET_TOWN,
        terrain=[list("░▓▓▓"), list("∙▓▓▓"), list("∙∙∙∙")],
        blockages={},
        known_sprite_ids=set(),
        sprite_interactions={},
        known_warp_ids={3},
        warp_usage_iterations={},
        known_map_boundaries=(),
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids=set(),
        object_interactions={},
        locked_door_interactions={},
        known_map_ids=frozenset(),
    )

    with (
        patch("overworld_map.service._update_overworld_map_terrain", new_callable=AsyncMock),
        patch("overworld_map.service.create_map_entity_memories", new_callable=AsyncMock),
        patch("overworld_map.service.remember_warps", new_callable=AsyncMock) as persist_warps,
    ):
        await update_overworld_map(1, cast("GameState", game_state), current_map)

    assert current_map.known_warp_ids == {1, 3}
    assert persist_warps.await_args is not None
    assert [warp.warp_id for warp in persist_warps.await_args.args[0]] == [1]
    tiles = get_navigation_tiles(current_map, cast("GameState", game_state))
    assert tiles[1, 1] == AsciiTile.WARP
    assert tiles[0, 0] == AsciiTile.UNSEEN
    assert tiles[1, 2] == AsciiTile.WALL


@pytest.mark.unit
async def test_loaded_terrain_refreshes_seen_tiles_without_revealing_unseen_tiles() -> None:
    """A remote door change updates known terrain; unseen cells stay hidden."""
    game_state = MagicMock()
    game_state.map = SimpleNamespace(id=MapId.PALLET_TOWN, height=2, width=3)
    game_state.screen = SimpleNamespace(top=0, left=0, bottom=1, right=1)
    game_state.get_ascii_screen_terrain.return_value = SimpleNamespace(
        ndarray=np.asarray([[AsciiTile.WALL]]), blockages={}
    )
    game_state.get_ascii_map_terrain.return_value = [
        [AsciiTile.FREE, AsciiTile.FREE, AsciiTile.WALL],
        [AsciiTile.FREE, AsciiTile.WALL, AsciiTile.FREE],
    ]
    game_state.is_text_on_screen.return_value = False
    game_state.warps = {}
    game_state.sprites = {}
    game_state.signs = {}
    game_state.objects = {}
    current_map = OverworldMap(
        id=MapId.PALLET_TOWN,
        terrain=[list("░▓▓"), list("▓▓░")],
        blockages={},
        known_sprite_ids=set(),
        sprite_interactions={},
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids=set(),
        object_interactions={},
        locked_door_interactions={},
        known_warp_ids=set(),
        warp_usage_iterations={},
        known_map_boundaries=(),
        known_map_ids=frozenset(),
    )

    with (
        patch("overworld_map.service.update_map_terrain", new_callable=AsyncMock),
        patch("overworld_map.service.create_map_entity_memories", new_callable=AsyncMock),
        patch("overworld_map.service.remember_warps", new_callable=AsyncMock),
    ):
        await update_overworld_map(1, cast("GameState", game_state), current_map)

    assert current_map.terrain == [list("▓∙▓"), list("∙▓░")]


@pytest.mark.unit
def test_derived_views_follow_current_entities_without_changing_terrain() -> None:
    """Presence, not camera rendering, controls whether a discovered sprite blocks routing."""
    current_map = OverworldMap(
        id=MapId.PALLET_TOWN,
        terrain=[list("∙∙∙")],
        blockages={},
        known_sprite_ids={1},
        sprite_interactions={},
        known_sign_ids=set(),
        sign_interactions={},
        known_object_ids=set(),
        object_interactions={},
        locked_door_interactions={},
        known_warp_ids=set(),
        warp_usage_iterations={},
        known_map_boundaries=(),
        known_map_ids=frozenset(),
    )
    sprite = SimpleNamespace(
        coords=Coords(row=0, col=1), is_rendered=True, label=SpriteLabel.BOULDER
    )
    sprites = {1: sprite}
    player = SimpleNamespace(coords=Coords(row=0, col=0))
    game_state = cast(
        "GameState",
        SimpleNamespace(
            sprites=sprites,
            warps={},
            signs={},
            objects={},
            pikachu=SimpleNamespace(is_rendered=False),
            player=player,
        ),
    )

    assert get_composed_map_tiles(current_map, game_state).tolist() == [
        [AsciiTile.PLAYER, AsciiTile.SPRITE, AsciiTile.FREE]
    ]
    assert get_navigation_tiles(current_map, game_state).tolist() == [
        [AsciiTile.FREE, AsciiTile.SPRITE, AsciiTile.FREE]
    ]

    sprite.coords = Coords(row=0, col=2)
    assert get_composed_map_tiles(current_map, game_state).tolist() == [
        [AsciiTile.PLAYER, AsciiTile.FREE, AsciiTile.SPRITE]
    ]
    assert get_accessible_coords(
        player.coords,
        get_navigation_tiles(current_map, game_state),
        TraversalRules(blockages={}, hm_tiles=frozenset(), directional_warps=frozenset()),
    ) == [Coords(row=0, col=0), Coords(row=0, col=1)]

    sprite.is_rendered = False
    assert get_navigation_tiles(current_map, game_state).tolist() == [
        [AsciiTile.FREE, AsciiTile.FREE, AsciiTile.SPRITE]
    ]

    del sprites[1]
    assert get_navigation_tiles(current_map, game_state).tolist() == [list("∙∙∙")]
    sprites[1] = sprite
    assert get_navigation_tiles(current_map, game_state)[0, 2] == AsciiTile.SPRITE
    assert current_map.terrain == [list("∙∙∙")]


@pytest.mark.unit
async def test_observed_cardinal_crossing_remembers_full_connection() -> None:
    """Persist a ROM-matched crossing even when it was not caused by a directional press."""
    connection = MapConnection(
        direction=FacingDirection.RIGHT,
        destination_map=MapId.ROUTE_4,
        source_coordinate_start=1,
        source_coordinate_end=4,
        destination_offset=Coords(row=0, col=-4),
        collision_tile_pairs=((None, None),) * 3,
    )
    source_map = SimpleNamespace(
        id=MapId.ROUTE_3,
        height=5,
        width=5,
        north_connection=None,
        south_connection=None,
        east_connection=connection,
        west_connection=None,
        is_connection_crossable=MagicMock(return_value=True),
    )
    previous_player = SimpleNamespace(coords=Coords(row=2, col=4))
    previous = cast(
        "GameState",
        SimpleNamespace(
            map=source_map,
            player=previous_player,
            warps={},
            screen=SimpleNamespace(to_screen_coords=MagicMock(return_value=None)),
            get_hm_tiles=MagicMock(return_value=[]),
        ),
    )
    current = cast(
        "GameState",
        SimpleNamespace(
            map=SimpleNamespace(id=MapId.ROUTE_4),
            player=SimpleNamespace(coords=Coords(row=2, col=0)),
        ),
    )

    with patch(
        "overworld_map.service.remember_map_boundaries",
        new_callable=AsyncMock,
    ) as persist_boundaries:
        await record_observed_map_boundary(previous, current)

        previous_player.coords = Coords(row=2, col=3)
        await record_observed_map_boundary(previous, current)

    persist_boundaries.assert_awaited_once()
    assert persist_boundaries.await_args is not None
    boundaries = persist_boundaries.await_args.args[0]
    assert {
        (
            boundary.map_id,
            boundary.activation,
            boundary.row,
            boundary.col,
            boundary.destination_map_id,
            boundary.destination_row,
            boundary.destination_col,
        )
        for boundary in boundaries
    } == {
        (MapId.ROUTE_3, WarpActivation.RIGHT, row, 4, MapId.ROUTE_4, row, 0) for row in range(1, 4)
    }


@pytest.mark.unit
async def test_stepping_onto_hole_remembers_one_way_connection() -> None:
    """Persist the observed fall without inventing a reverse connection."""
    previous = cast(
        "GameState",
        SimpleNamespace(
            map=SimpleNamespace(
                id=MapId.POKEMON_MANSION_3F,
                north_connection=None,
                south_connection=None,
                east_connection=None,
                west_connection=None,
            ),
            player=SimpleNamespace(coords=Coords(row=4, col=4)),
            warps={},
            screen=SimpleNamespace(to_screen_coords=MagicMock(return_value=Coords(row=0, col=0))),
            get_ascii_screen_terrain=MagicMock(
                return_value=SimpleNamespace(screen=[[AsciiTile.BOULDER_HOLE]])
            ),
        ),
    )
    current = cast(
        "GameState",
        SimpleNamespace(
            map=SimpleNamespace(id=MapId.POKEMON_MANSION_2F),
            player=SimpleNamespace(coords=Coords(row=7, col=8)),
        ),
    )

    with patch(
        "overworld_map.service.remember_map_boundaries",
        new_callable=AsyncMock,
    ) as persist_boundaries:
        await record_observed_hole_connection(
            button=Button.RIGHT,
            previous=previous,
            result=ControlResult(boundary=ControlBoundary.OVERWORLD_READY),
            current=current,
        )

    persist_boundaries.assert_awaited_once()
    assert persist_boundaries.await_args is not None
    (connection,) = persist_boundaries.await_args.args[0]
    assert connection.model_dump() == {
        "map_id": MapId.POKEMON_MANSION_3F,
        "activation": WarpActivation.STEP_ON,
        "row": 4,
        "col": 5,
        "destination_map_id": MapId.POKEMON_MANSION_2F,
        "destination_row": 7,
        "destination_col": 8,
    }
