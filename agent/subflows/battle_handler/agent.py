"""Pydantic AI battle-agent construction and execution."""

from pydantic_ai import Agent, BinaryContent, CallToolsNode
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.subflows.battle_handler.context import BattleContext
from agent.subflows.battle_handler.prompts import build_battle_decision_prompt
from agent.subflows.battle_handler.tools.registry import build_battle_toolset
from agent.subflows.battle_handler.utils import build_screenshot_content
from agent.utils import is_battle_handler_state
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


async def run_battle(context: BattleContext) -> None:
    """Run one agent conversation until the game exits battle mode."""
    agent = build_battle_agent(context)
    async with agent.iter(
        build_battle_agent_input(context),
        deps=context,
    ) as agent_run:
        try:
            node = agent_run.next_node
            while not agent.is_end_node(node):
                current_node = node
                if isinstance(current_node, CallToolsNode) and (
                    reasoning := current_node.model_response.text
                ):
                    context.state.rolling_memory.add_memory(reasoning)
                node = await agent_run.next(node)
                if isinstance(current_node, CallToolsNode) and not is_battle_handler_state(
                    context.game_state,
                ):
                    break
        finally:
            await update_pydantic_ai_usage(agent_run.new_messages())


def build_battle_agent_input(context: BattleContext) -> list[str | BinaryContent]:
    """Build the initial multimodal input for a battle-agent run."""
    return [
        build_screenshot_content(context.screenshot),
        build_battle_decision_prompt(context),
    ]
