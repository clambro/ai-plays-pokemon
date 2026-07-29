"""Pydantic AI battle-agent construction and execution."""

from io import BytesIO

from pydantic_ai import Agent, BinaryContent, CallToolsNode
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.subflows.battle_handler.context import BattleContext
from agent.subflows.battle_handler.prompts import build_battle_decision_prompt
from agent.subflows.battle_handler.tools.registry import build_battle_toolset
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS
from llm.usage import update_pydantic_ai_usage


def build_battle_agent(context: BattleContext) -> Agent[BattleContext, str]:
    """Construct the Pydantic AI battle agent."""
    return Agent(
        model=f"openai-responses:{MODEL}",
        name="battle_agent",
        deps_type=BattleContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[build_battle_toolset(context)],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=REASONING_EFFORT,
            openai_prompt_cache_key="battle-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )


async def run_battle_decision(context: BattleContext) -> None:
    """Run until the battle agent completes one valid action."""
    agent = build_battle_agent(context)
    async with agent.iter(
        build_battle_agent_input(context),
        deps=context,
    ) as agent_run:
        try:
            node = agent_run.next_node
            while not agent.is_end_node(node):
                current_node = node
                node = await agent_run.next(node)
                if isinstance(current_node, CallToolsNode):
                    break
        finally:
            await update_pydantic_ai_usage(agent_run.new_messages())


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
