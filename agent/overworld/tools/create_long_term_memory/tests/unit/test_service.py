"""Tests for deterministic long-term-memory creation."""

from unittest.mock import AsyncMock

import pytest

from agent.overworld.tools.create_long_term_memory import service


@pytest.mark.unit
async def test_create_long_term_memory_rejects_an_existing_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not overwrite a durable document through the creation boundary."""
    create_record = AsyncMock()
    monkeypatch.setattr(service, "create_long_term_memory_record", create_record)

    with pytest.raises(
        service.LongTermMemoryAlreadyExistsError,
        match=r"TEAM_PIKACHU.*already exists",
    ):
        await service.create_long_term_memory(
            title=" team pikachu ",
            content="Pikachu is the lead Pokemon.",
            iteration=12,
            existing_titles=("TEAM_PIKACHU",),
        )

    create_record.assert_not_awaited()
