"""Shared utilities for overworld tool execution."""

from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.dialog import settle_dialog
from agent.utils import build_screenshot_content

if TYPE_CHECKING:
    from agent.context import AgentContext

type OverworldToolResult = list[str | BinaryContent]


async def complete_overworld_action(
    context: AgentContext,
    action_result: str,
) -> OverworldToolResult:
    """Settle routine dialog and render a fresh overworld observation."""
    settlement = await settle_dialog(context)
    return [
        build_screenshot_content(settlement.screenshot),
        "\n\n".join(text for text in (action_result, settlement.transcript) if text),
    ]
