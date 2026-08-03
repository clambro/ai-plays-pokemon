"""Business logic for updating overworld sign descriptions."""

from typing import TYPE_CHECKING

from common.enums import MapEntityType
from database.map_entity_memory.repository import apply_map_entity_changes
from database.map_entity_memory.schemas import MapEntityMemoryUpdate

if TYPE_CHECKING:
    from collections.abc import Iterable

    from common.enums import MapId


async def update_signs(
    *,
    map_id: MapId,
    iteration: int,
    updates: Iterable[tuple[int, str]],
) -> None:
    """Persist description updates for signs on one map."""
    await apply_map_entity_changes(
        updates=[
            MapEntityMemoryUpdate(
                map_id=map_id,
                entity_id=index,
                entity_type=MapEntityType.SIGN,
                description=description,
                iteration=iteration,
            )
            for index, description in updates
        ],
    )
