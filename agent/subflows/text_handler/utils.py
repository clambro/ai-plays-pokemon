"""Shared utilities for the text subflow."""

import asyncio
from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.utils import DialogReader, build_screenshot_content, is_battle_handler_state
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from agent.subflows.text_handler.context import TextContext
    from emulator.game_state import YellowLegacyGameState

type TextToolResult = list[str | BinaryContent]


def is_text_interaction_state(game_state: YellowLegacyGameState) -> bool:
    """Check whether the current state still belongs to the text handler."""
    return game_state.is_text_on_screen() and not is_battle_handler_state(game_state)


def is_plain_text_dialog(game_state: YellowLegacyGameState) -> bool:
    """Check whether visible dialog can be advanced without a decision."""
    # Text outside the dialog box usually indicates a menu or yes/no question,
    # which must be left for the agent rather than advanced automatically.
    return (
        game_state.get_dialog_box() is not None
        and not game_state.is_text_on_screen(ignore_dialog_box=True)
        and not is_battle_handler_state(game_state)
    )


async def complete_text_action(
    context: TextContext,
    action_result: str,
) -> TextToolResult:
    """Advance ordinary dialog and return the resulting screen to the agent."""
    game_state = await context.emulator.get_game_state()
    dialog = ""
    if is_plain_text_dialog(game_state):
        dialog = await handle_text_dialog(context)
    game_state, screenshot = await context.emulator.get_game_state_with_screenshot()
    update_background_from_states(context.state, game_state)
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


async def handle_text_dialog(context: TextContext) -> str:
    """Advance ordinary dialog and record the text that was read."""
    dialog_reader = DialogReader(context.emulator)
    game_state = await dialog_reader.observe_current_state()
    if not is_plain_text_dialog(game_state):
        return ""

    is_blinking_cursor = True
    is_text_outside_dialog_box = True

    # The blinking cursor means that the dialog box is still scrolling. If there is no cursor
    # and no other text on screen, the dialog is done scrolling and we can press A one last time
    # to close it.
    while (
        game_state.get_dialog_box()
        and not is_battle_handler_state(game_state)
        and (is_blinking_cursor or not is_text_outside_dialog_box)
    ):
        await dialog_reader.advance()
        await asyncio.sleep(0.5)  # Buffer to ensure that no new dialog boxes have opened.
        game_state = await dialog_reader.observe_current_state()
        is_blinking_cursor = await dialog_reader.is_cursor_blinking()
        is_text_outside_dialog_box = game_state.is_text_on_screen(ignore_dialog_box=True)

    dialog = dialog_reader.text
    if dialog:
        dialog_status = " The dialog box is now closed." if not game_state.get_dialog_box() else ""
        context.state.rolling_memory.add_memory(
            content=f'Onscreen text: "{dialog}"{dialog_status}',
        )
    update_background_from_states(context.state, game_state)
    return dialog
