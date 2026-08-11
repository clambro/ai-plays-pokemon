"""Tests for the shared LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.responses.response_usage import (
    InputTokensDetails,
    OutputTokensDetails,
    ResponseUsage,
)

from agent.context import AgentContext
from agent.state import AgentState
from llm import service
from llm.usage import bind_llm_usage_updater

TEST_SYSTEM_PROMPT = "Test system prompt."


@pytest.mark.unit
async def test_get_llm_response_updates_agent_usage() -> None:
    """Record provider usage through the required agent-state updater."""
    expected_total_tokens = 12
    expected_cost = 0.00005135
    response = _response(
        output_text="response",
        usage=_usage(
            input_tokens=4,
            cached_tokens=1,
            cache_write_tokens=1,
            output_tokens=8,
        ),
    )
    client = MagicMock()
    client.responses.create = AsyncMock(return_value=response)
    context = AgentContext(
        state=AgentState(folder="output"),
        emulator=MagicMock(),
    )

    with (
        patch("llm.service.AsyncOpenAI", return_value=client),
        bind_llm_usage_updater(context.add_llm_usage),
    ):
        llm_service = service.OpenAILLMService()
        result = await llm_service.get_llm_response(
            "prompt",
            system_prompt=TEST_SYSTEM_PROMPT,
        )

    assert result == "response"
    assert context.state.total_tokens == expected_total_tokens
    assert context.state.total_cost == pytest.approx(expected_cost)
    client.responses.create.assert_awaited_once_with(
        model=service.MODEL,
        input="prompt",
        instructions=TEST_SYSTEM_PROMPT,
        reasoning={"effort": "low"},
    )


@pytest.mark.unit
def test_calculate_cost_applies_long_context_pricing() -> None:
    """Apply Luna's long-context multipliers to the entire response."""
    usage = _usage(
        input_tokens=272_001,
        cached_tokens=100_000,
        cache_write_tokens=50_000,
        output_tokens=10_000,
    )

    cost = service.OpenAILLMService._calculate_cost(service.MODEL, usage)

    expected_cost = (
        122_001 * 1.00 * 2 + 100_000 * 0.10 * 2 + 50_000 * 1.00 * 1.25 * 2 + 10_000 * 6.00 * 1.5
    ) / 1_000_000
    assert cost == pytest.approx(expected_cost)


@pytest.mark.unit
async def test_get_llm_response_rejects_incomplete_output() -> None:
    """Reject a terminal response that stopped before completion."""
    response = _response(status="incomplete")
    response.incomplete_details.reason = "max_output_tokens"
    client = MagicMock()
    client.responses.create = AsyncMock(return_value=response)

    with patch("llm.service.AsyncOpenAI", return_value=client):
        llm_service = service.OpenAILLMService()

    with (
        bind_llm_usage_updater(AsyncMock()),
        pytest.raises(ValueError, match="max_output_tokens"),
    ):
        await llm_service.get_llm_response(
            "prompt",
            system_prompt=TEST_SYSTEM_PROMPT,
        )


def _response(
    *,
    status: str = "completed",
    output_text: str = "",
    usage: ResponseUsage | None = None,
) -> MagicMock:
    """Create an OpenAI-like response for unit tests."""
    response = MagicMock()
    response.status = status
    response.output = []
    response.output_text = output_text
    response.usage = usage or _usage(input_tokens=1, output_tokens=1)
    response.model = service.MODEL
    response.error = None
    response.incomplete_details = MagicMock()
    return response


def _usage(
    *,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> ResponseUsage:
    """Create Responses API usage details."""
    return ResponseUsage(
        input_tokens=input_tokens,
        input_tokens_details=InputTokensDetails(
            cached_tokens=cached_tokens,
            cache_write_tokens=cache_write_tokens,
        ),
        output_tokens=output_tokens,
        output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
        total_tokens=input_tokens + output_tokens,
    )
