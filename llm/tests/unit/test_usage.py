"""Tests for local LLM usage accounting."""

import asyncio
from pathlib import Path

import pytest
from pydantic_ai import ModelResponse, RequestUsage

from agent.state import AgentState, AgentStore
from llm.usage import (
    bind_llm_usage_updater,
    update_llm_usage,
    update_pydantic_ai_usage,
)


@pytest.mark.unit
async def test_llm_usage_requires_an_active_agent_run() -> None:
    """Reject usage updates outside an agent-run context."""
    with pytest.raises(RuntimeError, match="not bound to an agent run"):
        await update_llm_usage(1, 0.01)


@pytest.mark.unit
async def test_agent_store_accumulates_concurrent_llm_usage() -> None:
    """Apply concurrent usage updates without losing any totals."""
    store = AgentStore(AgentState(folder=Path("output")))
    update_count = 20
    tokens_per_call = 10
    cost_per_call = 0.25

    with bind_llm_usage_updater(store.add_llm_usage):
        await asyncio.gather(
            *(update_llm_usage(tokens_per_call, cost_per_call) for _ in range(update_count)),
        )

    state = await store.get_state()
    assert state.total_tokens == update_count * tokens_per_call
    assert state.total_cost == pytest.approx(update_count * cost_per_call)


@pytest.mark.unit
async def test_pydantic_ai_usage_updates_agent_totals() -> None:
    """Accumulate Pydantic AI response tokens and calculated costs."""
    responses = [
        ModelResponse(
            parts=[],
            model_name="gpt-5.6-luna",
            provider_name="openai",
            usage=RequestUsage(input_tokens=100, output_tokens=10),
        ),
        ModelResponse(
            parts=[],
            model_name="gpt-5.6-luna",
            provider_name="openai",
            usage=RequestUsage(input_tokens=200, output_tokens=20),
        ),
    ]
    store = AgentStore(AgentState(folder=Path("output")))

    with bind_llm_usage_updater(store.add_llm_usage):
        await update_pydantic_ai_usage(responses)

    state = await store.get_state()
    assert state.total_tokens == sum(response.usage.total_tokens for response in responses)
    assert state.total_cost == pytest.approx(
        sum(float(response.cost().total_price) for response in responses),
    )
