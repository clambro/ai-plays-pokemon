"""Tests for deterministic long-term-memory updates."""

from unittest.mock import AsyncMock

import pytest

from agent.overworld.tools.update_long_term_memory import service
from agent.overworld.tools.update_long_term_memory.schemas import (
    UpdateType,
)
from database.long_term_memory.schemas import LongTermMemoryRead, LongTermMemoryUpdate


@pytest.mark.unit
@pytest.mark.parametrize(
    ("update_type", "new_content", "expected_content"),
    [
        (UpdateType.APPEND, "Use Electric attacks.", "Pikachu is fast.\nUse Electric attacks."),
        (UpdateType.REWRITE, "Pikachu is fast and reliable.", "Pikachu is fast and reliable."),
    ],
)
async def test_update_long_term_memory_applies_the_requested_operation(
    monkeypatch: pytest.MonkeyPatch,
    update_type: UpdateType,
    new_content: str,
    expected_content: str,
) -> None:
    """Persist and return the complete document after append or rewrite."""
    update_record = AsyncMock()
    monkeypatch.setattr(service, "update_long_term_memory_record", update_record)
    original = LongTermMemoryRead(title="TEAM_PIKACHU", content="Pikachu is fast.")

    result = await service.update_long_term_memory(
        title="team pikachu",
        update_type=update_type,
        content=new_content,
        iteration=23,
        loaded_memories={original.title: original},
    )

    assert result == LongTermMemoryRead(
        title="TEAM_PIKACHU",
        content=expected_content,
    )
    update_record.assert_awaited_once_with(
        LongTermMemoryUpdate(
            title="TEAM_PIKACHU",
            content=expected_content,
            iteration=23,
        ),
    )


@pytest.mark.unit
async def test_update_long_term_memory_rejects_an_unloaded_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Restrict updates to documents visible in the live agent state."""
    update_record = AsyncMock()
    monkeypatch.setattr(service, "update_long_term_memory_record", update_record)

    with pytest.raises(
        service.LongTermMemoryNotLoadedError,
        match=r"MAP_CERULEAN_CITY.*not currently loaded",
    ):
        await service.update_long_term_memory(
            title="map cerulean city",
            update_type=UpdateType.REWRITE,
            content="The gym leader is Misty.",
            iteration=23,
            loaded_memories={},
        )

    update_record.assert_not_awaited()
