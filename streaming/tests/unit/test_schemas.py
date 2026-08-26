"""Tests for streaming view schemas."""

from typing import TYPE_CHECKING

import pytest

from agent.state import AgentState
from streaming.schemas import LogEntryView

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.unit
def test_activity_log_uses_only_the_public_log(tmp_path: Path) -> None:
    """Keep private rolling memory out of the public activity log."""
    state = AgentState(folder=tmp_path, iteration=43)
    state.rolling_memory.add_memory("Private rolling memory.")
    state.public_log.add(41, "First public entry.")
    state.public_log.add(43, "Second public entry.")

    assert LogEntryView.from_public_log(state.public_log) == [
        LogEntryView(iteration=41, thought="First public entry."),
        LogEntryView(iteration=43, thought="Second public entry."),
    ]
