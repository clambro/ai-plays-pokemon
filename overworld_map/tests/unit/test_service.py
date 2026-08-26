"""Tests for explored-map behavior."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.enums import AsciiTile, Button, FacingDirection, MapEntityType, MapId, WarpActivation
from common.schemas import Coords
from database.map_entity_memory.schemas import MapEntityMemoryRead
from database.map_memory.schemas import MapMemoryRead
from database.route_memory.schemas import RouteTransitionCreate
from emulator.control_events import ControlBoundary, ControlResult
from emulator.parsers.map import MapConnection
from emulator.parsers.warp import WarpTransitionMemory
from overworld_map.schemas import OverworldMap
from overworld_map.service import (
    get_overworld_map,
    record_observed_route_transition,
    update_overworld_map,
)
from overworld_map.views import get_current_map_tiles, get_navigation_tiles

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
async def test_load_preserves_discovered_ids_without_live_records() -> None:
    """Persisted discoveries do not depend on records in one emulator snapshot."""
    interaction_iteration = 7
    memories = [
        MapEntityMemoryRead(
            map_id=MapId.PALLET_TOWN,
            entity_id=entity_id,
            entity_type=entity_type,
            last_interaction=(
                "Previously observed text."
                if entity_type in {MapEntityType.SPRITE, MapEntityType.SIGN, MapEntityType.OBJECT}
                else None
            ),
            last_interaction_iteration=interaction_iteration,
        )
        for entity_id, entity_type in enumerate(MapEntityType, start=1)
    ]
    game_state = cast("GameState", SimpleNamespace(map=_MAP_STATE))

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
        get_visited_maps=AsyncMock(return_value=[MapId.PALLET_TOWN]),
    ):
        current_map = await get_overworld_map(1, game_state)

    assert current_map.known_warp_ids == {1}
    assert current_map.warp_usage_iterations == {1: interaction_iteration}
    assert current_map.known_sprite_ids == {2}
    assert current_map.known_sign_ids == {3}
    assert current_map.known_object_ids == {4}
    assert current_map.sprite_interactions[2].text == "Previously observed text."
    assert current_map.sprite_interactions[2].iteration == interaction_iteration
    assert current_map.sign_interactions[3].text == "Previously observed text."
    assert current_map.sign_interactions[3].iteration == interaction_iteration
    assert current_map.object_interactions[4].text == "Previously observed text."
    assert current_map.object_interactions[4].iteration == interaction_iteration


@pytest.mark.unit
async def test_update_persists_discovery_and_derendering() -> None:
    """Visible discoveries are added and a de-rendered known sprite is removed."""
    visible = SimpleNamespace(
        sprites=[SimpleNamespace(index=3, is_rendered=True)],
        warps=[SimpleNamespace(index=4)],
        signs=[SimpleNamespace(index=5)],
        objects=[SimpleNamespace(index=6)],
    )
    game_state = MagicMock()
    game_state.map = _MAP_STATE
    game_state.sprites = {2: SimpleNamespace(coords=Coords(row=3, col=3), is_rendered=False)}
    game_state.screen.to_screen_coords.return_value = Coords(row=3, col=3)
    game_state.is_text_on_screen.return_value = False
    game_state.get_ascii_screen.return_value = visible
    current_map = cast(
        "OverworldMap",
        SimpleNamespace(
            id=MapId.PALLET_TOWN,
            known_sprite_ids={1, 2},
            sprite_interactions={2: SimpleNamespace()},
            known_warp_ids=set(),
            known_sign_ids=set(),
            known_object_ids=set(),
        ),
    )

    with (
        patch(
            "overworld_map.service.apply_map_entity_changes",
            new_callable=AsyncMock,
        ) as apply_changes,
        patch(
            "overworld_map.service._update_overworld_map_terrain",
            new_callable=AsyncMock,
        ),
    ):
        await update_overworld_map(1, cast("GameState", game_state), current_map)

    assert current_map.known_sprite_ids == {1, 3}
    assert current_map.sprite_interactions == {}
    assert current_map.known_warp_ids == {4}
    assert current_map.known_sign_ids == {5}
    assert current_map.known_object_ids == {6}
    assert apply_changes.await_args is not None
    changes = apply_changes.await_args.kwargs
    assert {(change.entity_type, change.entity_id) for change in changes["creates"]} == {
        (MapEntityType.SPRITE, 3),
        (MapEntityType.WARP, 4),
        (MapEntityType.SIGN, 5),
        (MapEntityType.OBJECT, 6),
    }
    assert [(change.entity_type, change.entity_id) for change in changes["deletes"]] == [
        (MapEntityType.SPRITE, 2)
    ]


@pytest.mark.unit
def test_derived_views_follow_current_entities_without_changing_terrain() -> None:
    """Known offscreen sprites block routing until their identity is removed."""
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
        known_warp_ids=set(),
        warp_usage_iterations={},
        known_map_ids=frozenset(),
        north_connection=None,
        south_connection=None,
        east_connection=None,
        west_connection=None,
    )
    sprite = SimpleNamespace(coords=Coords(row=0, col=1), is_rendered=True)
    player = SimpleNamespace(coords=Coords(row=0, col=0))
    game_state = cast(
        "GameState",
        SimpleNamespace(
            sprites={1: sprite},
            warps={},
            signs={},
            objects={},
            pikachu=SimpleNamespace(is_rendered=False),
            player=player,
        ),
    )

    assert get_current_map_tiles(current_map, game_state).tolist() == [
        [AsciiTile.PLAYER, AsciiTile.SPRITE, AsciiTile.FREE]
    ]
    assert get_navigation_tiles(current_map, game_state).tolist() == [
        [AsciiTile.FREE, AsciiTile.SPRITE, AsciiTile.FREE]
    ]

    sprite.coords = Coords(row=0, col=2)
    player.coords = Coords(row=0, col=1)
    assert get_current_map_tiles(current_map, game_state).tolist() == [
        [AsciiTile.FREE, AsciiTile.PLAYER, AsciiTile.SPRITE]
    ]

    sprite.is_rendered = False
    assert get_navigation_tiles(current_map, game_state).tolist() == [
        [AsciiTile.FREE, AsciiTile.FREE, AsciiTile.SPRITE]
    ]

    current_map.known_sprite_ids.remove(1)
    assert get_navigation_tiles(current_map, game_state).tolist() == [list("∙∙∙")]
    assert current_map.terrain == [list("∙∙∙")]


@pytest.mark.unit
async def test_records_only_a_directly_activated_ordinary_warp() -> None:
    """Reject a handoff or unrelated relocation while retaining a completed warp."""
    transition = WarpTransitionMemory(
        source_map_id=MapId.VIRIDIAN_CITY,
        source_warp_index=0,
        destination_warp_index=0,
    )
    source_coords = Coords(row=26, col=23)
    destination_coords = Coords(row=7, col=3)
    previous = MagicMock()
    previous.map.id = MapId.VIRIDIAN_CITY
    previous.player.coords = source_coords
    previous.warps = {
        0: SimpleNamespace(
            coords=Coords(row=25, col=23),
            activation=WarpActivation.STEP_ON,
            destination=MapId.VIRIDIAN_POKECENTER,
            destination_warp_index=0,
        )
    }
    current = MagicMock()
    current.map.id = MapId.VIRIDIAN_POKECENTER
    current.player.coords = destination_coords
    current.warp_transition = transition
    current.warps = {0: SimpleNamespace(coords=destination_coords)}
    create_transition = AsyncMock()

    with patch(
        "overworld_map.service.create_route_transition",
        new=create_transition,
    ):
        await record_observed_route_transition(
            iteration=7,
            button=Button.UP,
            previous=previous,
            result=ControlResult(boundary=ControlBoundary.OVERWORLD_READY),
            current=current,
        )
        create_transition.assert_awaited_once_with(
            7,
            RouteTransitionCreate(
                source_map_id=MapId.VIRIDIAN_CITY,
                source_coords=source_coords,
                button=Button.UP,
                warp_activation=WarpActivation.STEP_ON,
                destination_map_id=MapId.VIRIDIAN_POKECENTER,
                destination_coords=destination_coords,
            ),
        )

        create_transition.reset_mock()
        await record_observed_route_transition(
            iteration=8,
            button=Button.UP,
            previous=previous,
            result=ControlResult(boundary=ControlBoundary.TEXT_INPUT_READY),
            current=current,
        )
        previous.warps = {}
        await record_observed_route_transition(
            iteration=8,
            button=Button.UP,
            previous=previous,
            result=ControlResult(boundary=ControlBoundary.OVERWORLD_READY),
            current=current,
        )
        create_transition.assert_not_awaited()


@pytest.mark.unit
async def test_cardinal_transition_persistence_failure_does_not_interrupt_gameplay() -> None:
    """Recognize a direct boundary crossing while treating route memory as recoverable."""
    source_coords = Coords(row=19, col=6)
    destination_coords = Coords(row=0, col=6)
    connection = MapConnection(
        direction=FacingDirection.DOWN,
        destination_map=MapId.ROUTE_4,
        source_coordinate_start=0,
        source_coordinate_end=20,
        destination_offset=Coords(row=-19, col=0),
        collision_tile_pairs=tuple((0, 0) for _ in range(20)),
    )
    previous = MagicMock()
    previous.map.id = MapId.ROUTE_3
    previous.map.height = 20
    previous.map.south_connection = connection
    previous.player.coords = source_coords
    previous.warps = {}
    current = MagicMock()
    current.map.id = MapId.ROUTE_4
    current.player.coords = destination_coords
    current.warps = {}
    create_transition = AsyncMock(side_effect=RuntimeError("database unavailable"))

    with patch(
        "overworld_map.service.create_route_transition",
        new=create_transition,
    ):
        await record_observed_route_transition(
            iteration=7,
            button=Button.DOWN,
            previous=previous,
            result=ControlResult(boundary=ControlBoundary.OVERWORLD_READY),
            current=current,
        )

    assert create_transition.await_count == 1
