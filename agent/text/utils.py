"""Shared utilities for the text handler."""

from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.dialog import settle_dialog
from agent.formatting.game_state import build_screenshot_content
from agent.text.prompts import format_text_state_updates
from agent.utils import is_overworld_handler_state
from common.constants import ACTION_RESULT_LABEL

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState

type TextToolResult = list[str | BinaryContent]


async def complete_text_action(
    context: AgentContext,
    action_result: str,
    *,
    previous_game_state: GameState,
) -> TextToolResult:
    """Remember the action, settle dialog, and return the screen with changed state sections."""
    context.state.rolling_memory.add_memory(f"{ACTION_RESULT_LABEL} {action_result}")
    settlement = await settle_dialog(context)
    outcome = ""
    if is_overworld_handler_state(settlement.game_state, settlement.control_boundary):
        outcome = "The interaction ended; overworld control resumed."
        context.state.rolling_memory.add_memory(f"{ACTION_RESULT_LABEL} {outcome}")
    return [
        build_screenshot_content(settlement.screenshot),
        "\n\n".join(
            text
            for text in (
                action_result,
                settlement.transcript,
                format_text_state_updates(previous_game_state, settlement.game_state),
                settlement.game_state.screen.text,
                outcome,
                settlement.scripted_displacement_warning,
            )
            if text
        ),
    ]
