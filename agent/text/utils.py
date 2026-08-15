"""Shared utilities for the text handler."""

from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.utils import (
    build_screenshot_content,
    is_battle_handler_state,
)
from emulator.control_events import ControlBoundary
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState

type TextToolResult = list[str | BinaryContent]


def is_plain_text_dialog(game_state: GameState) -> bool:
    """Check whether visible dialog can be advanced without a decision."""
    # Text outside the dialog box usually indicates a menu or yes/no question,
    # which must be left for the agent rather than advanced automatically.
    return (
        game_state.screen.is_dialog_box_on_screen
        and not game_state.is_text_on_screen(ignore_dialog_box=True)
        and not is_battle_handler_state(game_state)
    )


async def complete_text_action(
    context: AgentContext,
    action_result: str,
) -> TextToolResult:
    """Advance ordinary dialog and return the resulting screen to the agent."""
    game_state, control_boundary = await context.emulator.get_game_state_with_control_boundary()
    dialog = ""
    if control_boundary == ControlBoundary.TEXT_INPUT_READY and is_plain_text_dialog(game_state):
        dialog = await handle_text_dialog(context)
    else:
        dialog = capture_pending_dialog(context, game_state)
    game_state, screenshot = await context.emulator.get_game_state_with_screenshot()
    return [
        build_screenshot_content(screenshot),
        "\n\n".join(
            text
            for text in (
                action_result,
                dialog,
                game_state.screen.text,
            )
            if text
        ),
    ]


async def handle_text_dialog(context: AgentContext) -> str:
    """Advance ordinary dialog and record the text that was read."""
    game_state, control_boundary = await context.emulator.get_game_state_with_control_boundary()
    if control_boundary != ControlBoundary.TEXT_INPUT_READY or not is_plain_text_dialog(game_state):
        return ""

    async def publish_before_input() -> None:
        current_state = await context.emulator.get_game_state()
        update_background_from_states(context.state, current_state)

    dialog = await context.emulator.advance_text_dialog(before_input=publish_before_input)
    final_state = await context.emulator.get_game_state()
    return _record_dialog(
        context,
        dialog,
        dialog_closed=not final_state.screen.is_dialog_box_on_screen,
    )


def capture_pending_dialog(context: AgentContext, game_state: GameState) -> str:
    """Record dialog whose interaction has already moved beyond standard text."""
    if is_battle_handler_state(game_state):
        return ""
    return _record_dialog(
        context,
        context.emulator.consume_pending_dialog(),
        dialog_closed=not game_state.screen.is_dialog_box_on_screen,
    )


def _record_dialog(
    context: AgentContext,
    dialog: str,
    *,
    dialog_closed: bool,
) -> str:
    """Append captured dialog to rolling memory and return it unchanged."""
    if dialog:
        dialog_status = " The dialog box is now closed." if dialog_closed else ""
        context.state.rolling_memory.add_memory(
            content=f'Onscreen text: "{dialog}"{dialog_status}',
        )
    return dialog
