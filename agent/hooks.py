"""Shared lifecycle hooks for gameplay agents."""

from typing import TYPE_CHECKING

from pydantic_ai.capabilities.hooks import Hooks

from agent.context import AgentContext
from emulator.control_events import ControlHandoff
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from pydantic_ai import ModelResponse, RunContext, ToolDefinition
    from pydantic_ai.capabilities import ValidatedToolArgs, WrapToolExecuteHandler
    from pydantic_ai.messages import ToolCallPart
    from pydantic_ai.models import ModelRequestContext


def require_tool_call(
    ctx: RunContext[AgentContext],  # noqa: ARG001
    request_context: ModelRequestContext,
) -> ModelRequestContext:
    """Require every gameplay-agent response to select an action tool."""
    if request_context.model_settings is None:
        request_context.model_settings = {}
    request_context.model_settings["tool_choice"] = "required"
    return request_context


async def record_model_response(
    ctx: RunContext[AgentContext],
    *,
    request_context: ModelRequestContext,  # noqa: ARG001
    response: ModelResponse,
) -> ModelResponse:
    """Account for a model response and retain its ordinary-text reasoning."""
    await ctx.deps.add_llm_usage(
        response.usage.total_tokens,
        float(response.cost().total_price),
    )
    if reasoning := response.text:
        ctx.deps.state.rolling_memory.add_memory(reasoning)
        ctx.deps.state.public_log.add(ctx.deps.state.iteration, reasoning)
    return response


async def publish_before_tool(
    ctx: RunContext[AgentContext],
    *,
    call: ToolCallPart,  # noqa: ARG001
    tool_def: ToolDefinition,  # noqa: ARG001
    args: dict[str, object],
) -> dict[str, object]:
    """Publish the completed decision immediately before its action begins."""
    game_state = await ctx.deps.emulator.get_game_state()
    update_background_from_states(ctx.deps.state, game_state)
    return args


async def handle_control_handoff(
    ctx: RunContext[AgentContext],
    *,
    call: ToolCallPart,  # noqa: ARG001
    tool_def: ToolDefinition,  # noqa: ARG001
    args: ValidatedToolArgs,
    handler: WrapToolExecuteHandler,
) -> object:
    """Turn an expected ROM-control handoff into normal tool completion."""
    try:
        return await handler(args)
    except ControlHandoff:
        ctx.deps.request_control_handoff()
        return "Control passed to a different gameplay handler before this action was accepted."


AGENT_HOOKS = Hooks[AgentContext](
    before_model_request=require_tool_call,
    after_model_request=record_model_response,
    before_tool_execute=publish_before_tool,
    tool_execute=handle_control_handoff,
)
