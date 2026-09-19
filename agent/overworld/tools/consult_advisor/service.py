"""Luna extra-high consultation using the existing map-inspection tool."""

from typing import TYPE_CHECKING

from pydantic_ai import Agent
from pydantic_ai.capabilities.hooks import Hooks
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.context import AgentContext
from agent.hooks import record_model_usage
from agent.overworld.prompts import ADVISOR_PROMPT
from agent.overworld.tools.inspect_map.interface import build_inspect_map_tool
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, TIMEOUT_SECONDS

if TYPE_CHECKING:
    from emulator.game_state import GameState


def build_advisor_agent(
    context: AgentContext,
    game_state: GameState,
) -> Agent[AgentContext, str]:
    """Build an advisory agent that can inspect known maps."""
    return Agent[AgentContext, str](
        model=f"openai-responses:{MODEL}",
        name="advisor_agent",
        deps_type=AgentContext,
        instructions=f"{SYSTEM_PROMPT}\n\n---\n\n{ADVISOR_PROMPT}",
        tools=[build_inspect_map_tool(context, game_state)],
        capabilities=[Hooks[AgentContext](after_model_request=record_model_usage)],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort="xhigh",
            openai_prompt_cache_key="advisor-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )
