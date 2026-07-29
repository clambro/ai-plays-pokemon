"""Shared utilities for the battle subflow."""

from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.subflows.battle_handler.prompts import build_battle_tool_result
from agent.utils import DialogReader, build_screenshot_content
from common.schemas import Coords
from streaming.server import update_background_from_states

if TYPE_CHECKING:
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
    return await refresh_battle_observation(
        context,
        action_result=action_result,
        dialog=dialog,
    )


async def refresh_battle_observation(
    context: BattleContext,
    *,
    action_result: str,
    dialog: str = "",
) -> BattleToolResult:
    """Capture and render a fresh battle observation for the agent."""
    game_state, screenshot = await context.emulator.get_game_state_with_screenshot()
    update_background_from_states(context.state, game_state)
    return [
        build_screenshot_content(screenshot),
        build_battle_tool_result(
            game_state,
            action_result=action_result,
            dialog=dialog,
        ),
    ]


async def handle_battle_dialog(context: BattleContext) -> str:
    """Advance battle dialog and record any text that was read.

    Args:
        context: Battle dependencies and rolling memory.

    Returns:
        The captured dialog text.
    """
    dialog_reader = DialogReader(context.emulator)
    game_state = await dialog_reader.wait_for_animation()
    while True:
        dialog_reader.observe(game_state)
        dialog_box = game_state.get_dialog_box()
        if not dialog_box:
            break

        if await dialog_reader.is_cursor_blinking():
            game_state = await dialog_reader.advance()
            continue

        previous_state = game_state
        game_state = await dialog_reader.wait_for_animation()
        if game_state.screen.text == previous_state.screen.text:
            break

    dialog = dialog_reader.text
    if dialog:
        context.state.rolling_memory.add_memory(
            content=f'Onscreen text: "{dialog}"',
        )
    return dialog
