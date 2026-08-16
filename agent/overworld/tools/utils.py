"""Shared utilities for overworld tool execution."""

from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.utils import build_screenshot_content

if TYPE_CHECKING:
    from agent.context import AgentContext

type OverworldToolResult = list[str | BinaryContent]


async def complete_overworld_action(
    context: AgentContext,
    action_result: str,
) -> OverworldToolResult:
    """Capture and render a fresh observation after an overworld tool call."""
    _, screenshot = await context.emulator.get_game_state_with_screenshot()
    dialog = context.emulator.consume_completed_dialog()
    if dialog:
        context.state.rolling_memory.add_memory(
            content=f'Onscreen text: "{dialog}"',
        )
    return [
        build_screenshot_content(screenshot),
        "\n\n".join(text for text in (action_result, dialog) if text),
    ]
