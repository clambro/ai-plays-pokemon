"""Pydantic AI battle-agent construction."""

from io import BytesIO

from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.subflows.battle_handler.context import BattleContext
from agent.subflows.battle_handler.prompts import build_battle_decision_prompt
from agent.subflows.battle_handler.tools.registry import BATTLE_TOOLSET
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS

BATTLE_AGENT = Agent(
    model=f"openai-responses:{MODEL}",
    name="battle_agent",
    deps_type=BattleContext,
    instructions=SYSTEM_PROMPT,
    model_settings=OpenAIResponsesModelSettings(
        openai_reasoning_effort=REASONING_EFFORT,
        openai_prompt_cache_key="battle-agent",
        parallel_tool_calls=False,
        timeout=TIMEOUT_SECONDS,
    ),
    toolsets=[BATTLE_TOOLSET],
)


def build_battle_agent_input(context: BattleContext) -> list[str | BinaryContent]:
    """Build the multimodal input for one battle-agent decision."""
    image_buffer = BytesIO()
    context.screenshot.save(image_buffer, format="PNG")
    return [
        BinaryContent(
            data=image_buffer.getvalue(),
            media_type="image/png",
            vendor_metadata={"detail": "original"},
        ),
        build_battle_decision_prompt(context),
    ]
