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
    dialog_result = settlement.transcript
    if dialog_result and not settlement.game_state.screen.is_dialog_box_on_screen:
        dialog_result += " The dialog box is now closed."
    return [
        build_screenshot_content(settlement.screenshot),
        "\n\n".join(
            text
            for text in (
                action_result,
                dialog_result,
                settlement.scripted_displacement_warning,
            )
            if text
        ),
    ]
