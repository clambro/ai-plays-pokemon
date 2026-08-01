"""Tests for preparing top-level agent state."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.enums import AgentStateHandler
from agent.nodes.prepare_agent_store import node
from agent.state import AgentState, AgentStore
from database.long_term_memory.schemas import LongTermMemoryRead
from memory.long_term_memory import LongTermMemory
from memory.rolling_memory import CurrentMemoryBlock, RollingMemory

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.unit
@pytest.mark.parametrize(
    ("prepared_iteration", "expected_titles"),
    [
        (7, set()),
        (6, {"TEAM_PIKACHU"}),
    ],
)
async def test_prepare_clears_loaded_memory_only_when_iteration_advances(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    prepared_iteration: int,
    expected_titles: set[str],
) -> None:
    """Preserve same-iteration retrievals but clear them for the next iteration."""
    memory = LongTermMemoryRead(title="TEAM_PIKACHU", content="Reliable Electric Pokemon.")
    state = AgentState(
        folder=tmp_path,
        iteration=6,
        rolling_memory=RollingMemory(current_block=CurrentMemoryBlock(iteration=6)),
        long_term_memory=LongTermMemory(pieces={memory.title: memory}),
    )
    store = AgentStore(state)
    monkeypatch.setattr(node, "wait_for_animations", AsyncMock())
    monkeypatch.setattr(
        node,
        "determine_handler",
        AsyncMock(return_value=AgentStateHandler.OVERWORLD),
    )
    monkeypatch.setattr(
        node,
        "initialize_memory",
        AsyncMock(
            return_value=RollingMemory(
                current_block=CurrentMemoryBlock(iteration=prepared_iteration),
            ),
        ),
    )
    monkeypatch.setattr(node, "update_background_log_from_memory", MagicMock())

    await node.PrepareAgentStoreNode(MagicMock()).service(store)

    prepared_state = await store.get_state()
    assert prepared_state.long_term_memory.pieces.keys() == expected_titles
