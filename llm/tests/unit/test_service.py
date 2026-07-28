"""Tests for the shared LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.responses.response_usage import (
    InputTokensDetails,
    OutputTokensDetails,
    ResponseUsage,
)
from PIL import Image
from pydantic import BaseModel

from agent.state import AgentState, AgentStore
from llm import service
from llm.usage import bind_llm_usage_updater


class SampleResponse(BaseModel):
    """Structured response used by the service tests."""

    value: str


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
    store = AgentStore(AgentState(folder="output"))

    with (
        patch("llm.service.AsyncOpenAI", return_value=client),
        bind_llm_usage_updater(store.add_llm_usage),
    ):
        llm_service = service.OpenAILLMService()
        result = await llm_service.get_llm_response("prompt")

    assert result == "response"
    state = await store.get_state()
    assert state.total_tokens == expected_total_tokens
    assert state.total_cost == pytest.approx(expected_cost)
    client.responses.create.assert_awaited_once_with(
        model=service.MODEL,
        input="prompt",
        instructions=service.SYSTEM_PROMPT,
        reasoning={"effort": "low"},
    )


@pytest.mark.unit
async def test_get_llm_response_pydantic_preserves_message_order() -> None:
    """Send images and text in their original order and return parsed output."""
    parsed = SampleResponse(value="parsed")
    response = _response(output_text=parsed.model_dump_json())
    client = MagicMock()
    client.responses.create = AsyncMock(return_value=response)
    usage_updater = AsyncMock()
    screenshot = Image.new("RGB", (1, 1))

    with (
        patch("llm.service.AsyncOpenAI", return_value=client),
        bind_llm_usage_updater(usage_updater),
    ):
        llm_service = service.OpenAILLMService()
        result = await llm_service.get_llm_response_pydantic(
            [screenshot, "prompt"],
            SampleResponse,
        )

    assert result == parsed
    await_args = client.responses.create.await_args
    assert await_args is not None
    request = await_args.kwargs
    content = request["input"][0]["content"]
    assert content[0]["type"] == "input_image"
    assert content[0]["detail"] == "original"
    assert content[0]["image_url"].startswith("data:image/png;base64,")
    assert content[1] == {"type": "input_text", "text": "prompt"}
    assert request["text"]["format"]["name"] == "SampleResponse"
    assert request["text"]["format"]["strict"] is True


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
        await llm_service.get_llm_response("prompt")


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
