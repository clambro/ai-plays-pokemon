"""Deterministic retrieval of long-term memory."""

from typing import TYPE_CHECKING

from loguru import logger

from database.long_term_memory.repository import get_long_term_memories
from memory.long_term_memory import LongTermMemory

if TYPE_CHECKING:
    from collections.abc import Collection


async def retrieve_long_term_memory(
    *,
    title: str,
    available_titles: Collection[str],
) -> LongTermMemory:
    """Load one selected long-term-memory document by title.

    Args:
        title: Memory title requested by the agent.
        available_titles: Titles currently available to the overworld run.

    Returns:
        The matching document, ready to append to the loaded memory set.
    """
    normalized_title = title.strip().upper().replace(" ", "_")
    if normalized_title not in available_titles:
        logger.warning(
            f"Tried to retrieve non-existent long-term memory piece: {normalized_title}. Skipping.",
        )
        return LongTermMemory()

    pieces = await get_long_term_memories([normalized_title])
    return LongTermMemory(pieces={piece.title: piece for piece in pieces})
