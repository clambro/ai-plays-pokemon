"""Tests for long-term-memory retrieval."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.nodes.retrieve_long_term_memory import service
from agent.nodes.retrieve_long_term_memory.schemas import RetrieveLongTermMemoryResponse
from database.long_term_memory.schemas import LongTermMemoryRead
from memory.long_term_memory import LongTermMemory


@pytest.mark.unit
async def test_retrieve_long_term_memory_loads_selected_titles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalize selected titles and discard titles that do not exist."""
    selected_title = "PEWTER_CITY"
    selected_memory = LongTermMemoryRead(
        title=selected_title,
        content="Brock leads the Pewter Gym.",
    )
    emulator = MagicMock()
    emulator.get_game_state_with_screenshot = AsyncMock(return_value=(MagicMock(), MagicMock()))
    get_titles = AsyncMock(return_value=["TEAM", selected_title])
    select_titles = AsyncMock(
        return_value=RetrieveLongTermMemoryResponse(titles=["Pewter City", "Missing memory"])
    )
    get_memories = AsyncMock(return_value=[selected_memory])
    monkeypatch.setattr(service, "get_all_long_term_memory_titles", get_titles)
    monkeypatch.setattr(service.llm_service, "get_llm_response_pydantic", select_titles)
    monkeypatch.setattr(service, "get_long_term_memories", get_memories)

    result = await service.retrieve_long_term_memory(
        long_term_memory=LongTermMemory(),
        state_string_builder=MagicMock(return_value="current state"),
        emulator=emulator,
    )

    assert result.pieces == {selected_title: selected_memory}
    get_memories.assert_awaited_once_with([selected_title])


@pytest.mark.unit
async def test_retrieve_long_term_memory_drops_unknown_titles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return no memories when none of the requested titles exist."""
    previous_memory = LongTermMemoryRead(
        title="Team",
        content="Pikachu is a permanent party member.",
    )
    previous = LongTermMemory(pieces={previous_memory.title: previous_memory})
    emulator = MagicMock()
    emulator.get_game_state_with_screenshot = AsyncMock(return_value=(MagicMock(), MagicMock()))
    get_memories = AsyncMock()
    monkeypatch.setattr(
        service,
        "get_all_long_term_memory_titles",
        AsyncMock(return_value=["Team"]),
    )
    monkeypatch.setattr(
        service.llm_service,
        "get_llm_response_pydantic",
        AsyncMock(return_value=RetrieveLongTermMemoryResponse(titles=["Missing memory"])),
    )
    monkeypatch.setattr(service, "get_long_term_memories", get_memories)

    result = await service.retrieve_long_term_memory(
        long_term_memory=previous,
        state_string_builder=MagicMock(return_value="current state"),
        emulator=emulator,
    )

    assert not result.pieces
    get_memories.assert_not_awaited()


@pytest.mark.unit
async def test_retrieve_long_term_memory_skips_selection_without_titles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return an empty selection without calling the model when no memories exist."""
    emulator = MagicMock()
    select_titles = AsyncMock()
    monkeypatch.setattr(
        service,
        "get_all_long_term_memory_titles",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(service.llm_service, "get_llm_response_pydantic", select_titles)

    result = await service.retrieve_long_term_memory(
        long_term_memory=LongTermMemory(),
        state_string_builder=MagicMock(return_value="current state"),
        emulator=emulator,
    )

    assert not result.pieces
    select_titles.assert_not_awaited()
    emulator.get_game_state_with_screenshot.assert_not_called()
