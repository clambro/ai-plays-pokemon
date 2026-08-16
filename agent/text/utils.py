"""Shared utilities for the text handler."""

from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.dialog import settle_dialog
from agent.utils import build_screenshot_content

if TYPE_CHECKING:
    from agent.context import AgentContext

type TextToolResult = list[str | BinaryContent]


async def complete_text_action(
    context: AgentContext,
    action_result: str,
) -> TextToolResult:
    """Advance ordinary dialog and return the resulting screen to the agent."""
    settlement = await settle_dialog(context)
    return [
        build_screenshot_content(settlement.screenshot),
        "\n\n".join(
            text
            for text in (
                action_result,
                settlement.transcript,
                settlement.game_state.screen.text,
            )
            if text
        ),
    ]
