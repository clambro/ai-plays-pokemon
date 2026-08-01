"""Tests for deterministic long-term-memory retrieval."""

from unittest.mock import AsyncMock

import pytest

from agent.subflows.overworld_handler.tools.retrieve_long_term_memory import service
from database.long_term_memory.schemas import LongTermMemoryRead


@pytest.mark.unit
async def test_retrieve_long_term_memory_loads_an_available_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalize and load one requested title."""
    selected_memory = LongTermMemoryRead(
        title="PEWTER_CITY",
        content="Brock leads the Pewter Gym.",
    )
    get_memories = AsyncMock(return_value=[selected_memory])
    monkeypatch.setattr(service, "get_long_term_memories", get_memories)

    result = await service.retrieve_long_term_memory(
        title="Pewter City",
        available_titles=("PEWTER_CITY", "TEAM_PIKACHU"),
    )

    assert result.pieces == {selected_memory.title: selected_memory}
    get_memories.assert_awaited_once_with(["PEWTER_CITY"])


@pytest.mark.unit
async def test_retrieve_long_term_memory_rejects_an_unknown_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return an empty memory set without querying an unknown title."""
    get_memories = AsyncMock()
    monkeypatch.setattr(service, "get_long_term_memories", get_memories)

    result = await service.retrieve_long_term_memory(
        title="MISSING_MEMORY",
        available_titles=("TEAM_PIKACHU",),
    )

    assert not result.pieces
    get_memories.assert_not_awaited()
