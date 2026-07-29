"""Pydantic AI text-agent construction and one-action execution."""

from pydantic_ai import Agent, BinaryContent, CallToolsNode, ModelResponse
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from agent.subflows.text_handler.context import TextContext
from agent.subflows.text_handler.prompts import build_text_decision_prompt
from agent.subflows.text_handler.tools.registry import build_text_toolset
from agent.utils import build_screenshot_content
from common.prompts import SYSTEM_PROMPT
from llm.service import MODEL, REASONING_EFFORT, TIMEOUT_SECONDS
from llm.usage import update_pydantic_ai_usage


def build_text_agent(context: TextContext) -> Agent[TextContext, str]:
    """Construct the Pydantic AI text agent."""
    return Agent(
        model=f"openai-responses:{MODEL}",
        name="text_agent",
        deps_type=TextContext,
        instructions=SYSTEM_PROMPT,
        toolsets=[build_text_toolset(context)],
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_effort=REASONING_EFFORT,
            openai_prompt_cache_key="text-agent",
            parallel_tool_calls=False,
            timeout=TIMEOUT_SECONDS,
        ),
    )


async def run_text_agent(context: TextContext) -> None:
    """Run the text agent through at most one tool action."""
    agent = build_text_agent(context)
    async with agent.iter(
        build_text_agent_input(context),
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
                    break
        finally:
            responses = [
                message
                for message in agent_run.new_messages()
                if isinstance(message, ModelResponse)
            ]
            for response in responses[accounted_responses:]:
                await _record_response_usage(context, response)


def build_text_agent_input(context: TextContext) -> list[str | BinaryContent]:
    """Build the initial multimodal input for a text-agent run."""
    return [
        build_screenshot_content(context.screenshot),
        build_text_decision_prompt(context),
    ]


async def _record_response_usage(context: TextContext, response: ModelResponse) -> None:
    """Record one model response in both persistent and displayed state."""
    tokens, cost = await update_pydantic_ai_usage(response)
    context.state.total_tokens += tokens
    context.state.total_cost += cost
