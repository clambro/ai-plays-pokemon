"""Deterministic updates to long-term memory."""

from typing import TYPE_CHECKING

from agent.subflows.overworld_handler.tools.update_long_term_memory.schemas import (
    UpdateType,
)
from database.long_term_memory.repository import (
    update_long_term_memory as update_long_term_memory_record,
)
from database.long_term_memory.schemas import LongTermMemoryRead, LongTermMemoryUpdate

if TYPE_CHECKING:
    from collections.abc import Mapping


class LongTermMemoryNotLoadedError(ValueError):
    """Raised when an update targets a memory absent from live state."""


async def update_long_term_memory(
    *,
    title: str,
    update_type: UpdateType,
    content: str,
    iteration: int,
    loaded_memories: Mapping[str, LongTermMemoryRead],
) -> LongTermMemoryRead:
    """Update and persist one currently loaded long-term-memory document.

    Args:
        title: Title of the loaded document to update.
        update_type: Whether to append to or rewrite the document.
        content: New content to append or use as a replacement.
        iteration: Current workflow iteration used as the update timestamp.
        loaded_memories: Documents currently available to the agent.

    Returns:
        The complete updated memory.

    Raises:
        LongTermMemoryNotLoadedError: The normalized title is not loaded.
    """
    normalized_title = title.strip().upper().replace(" ", "_")
    original = loaded_memories.get(normalized_title)
    if original is None:
        raise LongTermMemoryNotLoadedError(
            f"Long-term memory '{normalized_title}' is not currently loaded; no update was made.",
        )

    updated_content = (
        f"{original.content}\n{content}" if update_type == UpdateType.APPEND else content
    )
    memory = LongTermMemoryRead(title=normalized_title, content=updated_content)
    await update_long_term_memory_record(
        LongTermMemoryUpdate(
            title=memory.title,
            content=memory.content,
            iteration=iteration,
        ),
    )
    return memory
