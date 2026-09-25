"""Pydantic AI advisor-agent construction."""

from typing import TYPE_CHECKING

from pydantic_ai import Agent
from pydantic_ai.capabilities.hooks import Hooks
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.context import AgentContext
from agent.hooks import record_model_usage
from agent.overworld.prompts import ADVISOR_PROMPT
from agent.overworld.tools.inspect_map.interface import build_inspect_map_tool
from common.enums import ReasoningEffort
from common.prompts import SYSTEM_PROMPT
from llm.service import build_agent_model

if TYPE_CHECKING:
    from emulator.game_state import GameState

ADVISOR_TIMEOUT_SECONDS = 120


def build_advisor_agent(
    context: AgentContext,
    game_state: GameState,
) -> Agent[AgentContext, str]:
    """Build an advisory agent that can inspect known maps."""
    return Agent[AgentContext, str](
        # A timed-out consultation should return to gameplay, not repeat the long request.
        model=build_agent_model(max_retries=0),
        name="advisor_agent",
        deps_type=AgentContext,
        instructions=f"{SYSTEM_PROMPT}\n\n---\n\n{ADVISOR_PROMPT}",
        tools=[build_inspect_map_tool(context, game_state)],
        capabilities=[Hooks[AgentContext](after_model_request=record_model_usage)],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=ReasoningEffort.MEDIUM.value,
            openai_prompt_cache_key="advisor-agent",
            parallel_tool_calls=False,
            timeout=ADVISOR_TIMEOUT_SECONDS,
        ),
    )
