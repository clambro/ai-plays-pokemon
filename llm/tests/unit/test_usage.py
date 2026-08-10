"""Tests for local LLM usage accounting."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent.context import AgentContext
from agent.state import AgentState
from llm.usage import (
    bind_llm_usage_updater,
    update_llm_usage,
)


@pytest.mark.unit
async def test_llm_usage_requires_an_active_agent_run() -> None:
    """Reject usage updates outside an agent-run context."""
    with pytest.raises(RuntimeError, match="not bound to an agent run"):
        await update_llm_usage(1, 0.01)


@pytest.mark.unit
async def test_agent_context_accumulates_concurrent_llm_usage() -> None:
    """Apply concurrent usage updates without losing any totals."""
    context = AgentContext(
        state=AgentState(folder=Path("output")),
        emulator=MagicMock(),
    )
    update_count = 20
    tokens_per_call = 10
    cost_per_call = 0.25

    with bind_llm_usage_updater(context.add_llm_usage):
        await asyncio.gather(
            *(update_llm_usage(tokens_per_call, cost_per_call) for _ in range(update_count)),
        )

    assert context.state.total_tokens == update_count * tokens_per_call
    assert context.state.total_cost == pytest.approx(update_count * cost_per_call)
