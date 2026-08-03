"""Business logic for updating overworld sprite descriptions."""

from typing import TYPE_CHECKING

from common.enums import MapEntityType
from database.map_entity_memory.repository import apply_map_entity_changes
from database.map_entity_memory.schemas import MapEntityMemoryUpdate

if TYPE_CHECKING:
    from collections.abc import Iterable

    from common.enums import MapId


async def update_sprites(
    *,
    map_id: MapId,
    iteration: int,
    updates: Iterable[tuple[int, str]],
) -> None:
    """Persist description updates for sprites on one map."""
    await apply_map_entity_changes(
        updates=[
            MapEntityMemoryUpdate(
                map_id=map_id,
                entity_id=index,
                entity_type=MapEntityType.SPRITE,
                description=description,
                iteration=iteration,
            )
            for index, description in updates
        ],
    )
