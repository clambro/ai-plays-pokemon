"""Deterministic creation of long-term memory."""

from typing import TYPE_CHECKING

from database.long_term_memory.repository import (
    create_long_term_memory as create_long_term_memory_record,
)
from database.long_term_memory.schemas import LongTermMemoryCreate, LongTermMemoryRead

if TYPE_CHECKING:
    from collections.abc import Collection


class LongTermMemoryAlreadyExistsError(ValueError):
    """Raised when creation targets an existing memory title."""


async def create_long_term_memory(
    *,
    title: str,
    content: str,
    iteration: int,
    existing_titles: Collection[str],
) -> LongTermMemoryRead:
    """Create and persist one long-term-memory document.

    Args:
        title: Proposed unique title. It is normalized to uppercase with spaces
            replaced by underscores.
        content: Complete document content to persist.
        iteration: Current agent iteration used as the creation timestamp.
        existing_titles: Titles that already exist in persistent memory.

    Returns:
        The normalized memory that was persisted.

    Raises:
        LongTermMemoryAlreadyExistsError: The normalized title already exists.
    """
    normalized_title = title.strip().upper().replace(" ", "_")
    if normalized_title in existing_titles:
        raise LongTermMemoryAlreadyExistsError(
            f"Long-term memory '{normalized_title}' already exists; no memory was created.",
        )

    memory = LongTermMemoryRead(title=normalized_title, content=content)
    await create_long_term_memory_record(
        LongTermMemoryCreate(
            title=memory.title,
            content=memory.content,
            iteration=iteration,
        ),
    )
    return memory
