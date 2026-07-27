"""Tests for the shared LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.state import AgentState, AgentStore
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService
from llm.usage import bind_llm_usage_updater


@pytest.mark.unit
async def test_get_llm_response_updates_agent_usage() -> None:
    """Record provider usage through the required agent-state updater."""
    expected_total_tokens = 12
    expected_cost = 0.0000212
    response = MagicMock()
    response.text = "response"
    response.usage_metadata.prompt_token_count = 4
    response.usage_metadata.thoughts_token_count = 3
    response.usage_metadata.candidates_token_count = 5
    response.usage_metadata.total_token_count = expected_total_tokens

    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)
    store = AgentStore(AgentState(folder="output"))

    with (
        patch("llm.service.genai.Client", return_value=client),
        patch("llm.service.create_llm_message", new_callable=AsyncMock) as create_llm_message,
        bind_llm_usage_updater(store.add_llm_usage),
    ):
        service = GeminiLLMService(GEMINI_FLASH_2_5)
        result = await service.get_llm_response(
            "prompt",
            prompt_name="test",
        )

    assert result == "response"
    state = await store.get_state()
    assert state.total_tokens == expected_total_tokens
    assert state.total_cost == pytest.approx(expected_cost)
    create_llm_message.assert_awaited_once()
