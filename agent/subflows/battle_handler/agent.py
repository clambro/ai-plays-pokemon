"""Pydantic AI battle-agent construction and execution."""

from typing import TYPE_CHECKING

from pydantic_ai import (
    Agent,
    BinaryContent,
    CallToolsNode,
    ModelResponse,
)
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.subflows.battle_handler.context import BattleContext
from agent.subflows.battle_handler.prompts import build_battle_decision_prompt
from agent.subflows.battle_handler.tools.registry import build_battle_toolset
from agent.utils import build_screenshot_content, is_battle_handler_state
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS
from llm.usage import update_pydantic_ai_usage

if TYPE_CHECKING:
    from PIL import Image

    from common.enums import BattleType
    from emulator.game_state import YellowLegacyGameState


def build_battle_agent(
    context: BattleContext,
    battle_type: BattleType | None,
) -> Agent[BattleContext, str]:
    """Construct the Pydantic AI battle agent."""
    return Agent(
        model=f"openai-responses:{MODEL}",
        name="battle_agent",
        deps_type=BattleContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[build_battle_toolset(context, battle_type)],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=REASONING_EFFORT,
            openai_prompt_cache_key="battle-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )


async def run_battle(context: BattleContext) -> None:
    """Run one agent conversation until the game exits battle mode."""
    initial_game_state, initial_screenshot = await context.emulator.get_game_state_with_screenshot()
    agent = build_battle_agent(
        context,
        initial_game_state.battle.battle_type,
    )
    async with agent.iter(
        build_battle_agent_input(
            context,
            initial_game_state=initial_game_state,
            initial_screenshot=initial_screenshot,
        ),
        deps=context,
    ) as agent_run:
        accounted_responses = 0
        try:
            node = agent_run.next_node
            while not agent.is_end_node(node):
                current_node = node
                if isinstance(current_node, CallToolsNode):
                    await _record_response_usage(context, current_node.model_response)
                    accounted_responses += 1
                    if reasoning := current_node.model_response.text:
                        context.state.rolling_memory.add_memory(reasoning)
                node = await agent_run.next(node)
                if isinstance(current_node, CallToolsNode):
                    game_state = await context.emulator.get_game_state()
                    if not is_battle_handler_state(game_state):
                        break
        finally:
            responses = [
                message
                for message in agent_run.new_messages()
                if isinstance(message, ModelResponse)
            ]
            for response in responses[accounted_responses:]:
                await _record_response_usage(context, response)


def build_battle_agent_input(
    context: BattleContext,
    *,
    initial_game_state: YellowLegacyGameState,
    initial_screenshot: Image.Image,
) -> list[str | BinaryContent]:
    """Build the initial multimodal input for a battle-agent run."""
    return [
        build_screenshot_content(initial_screenshot),
        build_battle_decision_prompt(context, initial_game_state),
    ]


async def _record_response_usage(context: BattleContext, response: ModelResponse) -> None:
    """Record one model response in both persistent and displayed state."""
    tokens, cost = await update_pydantic_ai_usage(response)
    context.state.total_tokens += tokens
    context.state.total_cost += cost
