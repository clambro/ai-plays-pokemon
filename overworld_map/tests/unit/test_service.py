"""Tests for explored-map entity discovery."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.enums import MapEntityType, MapId
from common.schemas import Coords
from database.map_entity_memory.schemas import MapEntityMemoryRead
from database.map_memory.schemas import MapMemoryRead
from overworld_map.service import get_overworld_map, update_overworld_map

if TYPE_CHECKING:
    from emulator.game_state import GameState
    from overworld_map.schemas import OverworldMap

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
    memories = [
        MapEntityMemoryRead(
            map_id=MapId.PALLET_TOWN,
            entity_id=entity_id,
            entity_type=entity_type,
        )
        for entity_id, entity_type in enumerate(MapEntityType, start=1)
    ]
    game_state = cast("GameState", SimpleNamespace(map=_MAP_STATE))

    with patch.multiple(
        "overworld_map.service",
        get_map_memory=AsyncMock(
            return_value=MapMemoryRead(
                map_id=MapId.PALLET_TOWN,
                tiles="∙",
                blockages={},
            ),
        ),
        get_map_entity_memories_for_map=AsyncMock(return_value=memories),
        get_visited_maps=AsyncMock(return_value=[MapId.PALLET_TOWN]),
    ):
        current_map = await get_overworld_map(1, game_state)

    assert current_map.known_warp_ids == {1}
    assert current_map.known_sprite_ids == {2}
    assert current_map.known_sign_ids == {3}


@pytest.mark.unit
async def test_update_persists_discovery_and_derendering() -> None:
    """Visible discoveries are added and a de-rendered known sprite is removed."""
    visible = SimpleNamespace(
        sprites=[SimpleNamespace(index=3, is_rendered=True)],
        warps=[SimpleNamespace(index=4)],
        signs=[SimpleNamespace(index=5)],
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
            known_warp_ids=set(),
            known_sign_ids=set(),
        ),
    )

    with (
        patch(
            "overworld_map.service.apply_map_entity_changes",
            new_callable=AsyncMock,
        ) as apply_changes,
        patch(
            "overworld_map.service._update_overworld_map_tiles",
            new_callable=AsyncMock,
        ),
    ):
        await update_overworld_map(1, cast("GameState", game_state), current_map)

    assert current_map.known_sprite_ids == {1, 3}
    assert current_map.known_warp_ids == {4}
    assert current_map.known_sign_ids == {5}
    assert apply_changes.await_args is not None
    changes = apply_changes.await_args.kwargs
    assert {(change.entity_type, change.entity_id) for change in changes["creates"]} == {
        (MapEntityType.SPRITE, 3),
        (MapEntityType.WARP, 4),
        (MapEntityType.SIGN, 5),
    }
    assert [(change.entity_type, change.entity_id) for change in changes["deletes"]] == [
        (MapEntityType.SPRITE, 2)
    ]
