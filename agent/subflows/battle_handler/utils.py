"""Shared utilities for the battle subflow."""

from io import BytesIO
from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.subflows.battle_handler.prompts import build_battle_tool_result
from agent.utils import append_dialog_to_list_inplace, is_blinking_cursor_on_screen
from common.enums import Button
from common.schemas import Coords
from streaming.server import update_background_from_states

if TYPE_CHECKING:
    from PIL import Image

    from agent.subflows.battle_handler.context import BattleContext
    from emulator.game_state import YellowLegacyGameState

type BattleToolResult = list[str | BinaryContent]


def is_fight_menu_open(game_state: YellowLegacyGameState) -> bool:
    """Check if the fight menu is open.

    Args:
        game_state: Current game state to inspect.

    Returns:
        Whether the standard fight menu is visible.
    """
    screen_text = game_state.screen.text.replace(" ", "").replace("\n", "").replace("▶", "")
    return "FIGHTPKMNITEMRUN" in screen_text


def get_cursor_pos_in_fight_menu(game_state: YellowLegacyGameState) -> Coords | None:
    """Get the cursor position in the fight menu.

    Args:
        game_state: Current game state to inspect.

    Returns:
        The cursor's row and column, or ``None`` when the fight menu is not open.
    """
    if not is_fight_menu_open(game_state):
        return None
    text = game_state.screen.text
    if "▶FIGHT" in text:
        return Coords(row=0, col=0)
    if "▶PKMN" in text:
        return Coords(row=0, col=1)
    if "▶ITEM" in text:
        return Coords(row=1, col=0)
    if "▶RUN" in text:
        return Coords(row=1, col=1)
    return None


async def complete_battle_action(context: BattleContext, action_result: str) -> BattleToolResult:
    """Advance dialog, refresh state, and build the in-run tool result.

    Args:
        context: Mutable battle-agent dependencies.
        action_result: Description of the completed emulator input.

    Returns:
        Fresh context for the agent's next decision.
    """
    dialog = await handle_battle_dialog(context)
    result = await refresh_battle_observation(
        context,
        action_result=action_result,
        dialog=dialog,
    )
    return [result, build_screenshot_content(context.screenshot)]


async def refresh_battle_observation(
    context: BattleContext,
    *,
    action_result: str,
    dialog: str = "",
) -> str:
    """Refresh the battle context and render it for the agent."""
    await refresh_battle_context(context)
    return build_battle_tool_result(
        context,
        action_result=action_result,
        dialog=dialog,
    )


async def refresh_battle_context(context: BattleContext) -> None:
    """Refresh local and displayed state from the emulator."""
    game_state, screenshot = await context.emulator.get_game_state_with_screenshot()
    context.game_state = game_state
    context.screenshot = screenshot
    update_background_from_states(context.state, game_state)


def build_screenshot_content(screenshot: Image.Image) -> BinaryContent:
    """Encode a screenshot for a multimodal model message."""
    image_buffer = BytesIO()
    screenshot.save(image_buffer, format="PNG")
    return BinaryContent(
        data=image_buffer.getvalue(),
        media_type="image/png",
        vendor_metadata={"detail": "original"},
    )


async def handle_battle_dialog(context: BattleContext) -> str:
    """Advance battle dialog and record any text that was read.

    Args:
        context: Battle dependencies and rolling memory.

    Returns:
        The captured dialog text.
    """
    text: list[str] = []
    await context.emulator.wait_for_animation_to_finish()
    while True:
        game_state = await context.emulator.get_game_state()
        dialog_box = game_state.get_dialog_box()
        if not dialog_box:
            break
        append_dialog_to_list_inplace(text, dialog_box)

        if await is_blinking_cursor_on_screen(context.emulator):
            await context.emulator.press_button(Button.A)
            continue

        previous_state = game_state
        await context.emulator.wait_for_animation_to_finish()
        game_state = await context.emulator.get_game_state()
        if game_state.screen.text == previous_state.screen.text:
            break

    dialog = " ".join(text).strip()
    if dialog:
        context.state.rolling_memory.add_memory(
            content=f'The following text was read from the battle dialog box: "{dialog}"',
        )
    return dialog
