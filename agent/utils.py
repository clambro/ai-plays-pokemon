"""Shared utilities and lifecycle hooks for gameplay agents."""

from io import BytesIO
from typing import TYPE_CHECKING

from pydantic_ai import (
    BinaryContent,
    ModelResponse,
    RunContext,
    ToolDefinition,
)
from pydantic_ai.capabilities.hooks import Hooks

from agent.context import AgentContext
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from PIL import Image
    from pydantic_ai.messages import ToolCallPart
    from pydantic_ai.models import ModelRequestContext

    from emulator.game_state import GameState


def build_screenshot_content(screenshot: Image.Image) -> BinaryContent:
    """Encode a screenshot for a multimodal model message."""
    image_buffer = BytesIO()
    screenshot.save(image_buffer, format="PNG")
    return BinaryContent(
        data=image_buffer.getvalue(),
        media_type="image/png",
        vendor_metadata={"detail": "original"},
    )


def is_battle_handler_state(game_state: GameState) -> bool:
    """Determine whether the game state belongs to the battle handler."""
    # The nickname screen after catching a Pokemon is considered a battle state by the game,
    # but we need to route it to the text handler instead.
    return game_state.battle.is_in_battle and not game_state.is_naming_screen()


def is_text_handler_state(game_state: GameState) -> bool:
    """Determine whether the current state belongs to the text handler."""
    return not is_battle_handler_state(game_state) and (
        game_state.is_text_on_screen() or game_state.map.height == 0 or game_state.map.width == 0
    )


def is_overworld_handler_state(game_state: GameState) -> bool:
    """Determine whether the current state belongs to the overworld handler."""
    return not is_battle_handler_state(game_state) and not is_text_handler_state(game_state)


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
    return response


async def publish_before_tool(
    ctx: RunContext[AgentContext],
    *,
    call: ToolCallPart,  # noqa: ARG001
    tool_def: ToolDefinition,  # noqa: ARG001
    args: dict[str, object],
) -> dict[str, object]:
    """Publish shared state before an ordinary function tool executes."""
    game_state = await ctx.deps.emulator.get_game_state()
    update_background_from_states(ctx.deps.state, game_state)
    return args


AGENT_HOOKS = Hooks[AgentContext](
    after_model_request=record_model_response,
    before_tool_execute=publish_before_tool,
)
