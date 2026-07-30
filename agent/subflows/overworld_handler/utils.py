"""Shared utilities for overworld tool execution."""

from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.utils import build_screenshot_content
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from agent.subflows.overworld_handler.context import OverworldContext

type OverworldToolResult = list[str | BinaryContent]


async def complete_overworld_action(
    context: OverworldContext,
    action_result: str,
) -> OverworldToolResult:
    """Capture and render a fresh observation after an overworld tool call."""
    game_state, screenshot = await context.emulator.get_game_state_with_screenshot()
    update_background_from_states(context.state, game_state)
    return [
        build_screenshot_content(screenshot),
        action_result,
    ]
