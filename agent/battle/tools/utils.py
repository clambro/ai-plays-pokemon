"""Shared utilities for the battle handler."""

from typing import TYPE_CHECKING

from pydantic_ai import BinaryContent

from agent.battle.formatting import format_available_pokeballs, format_battle_info
from agent.dialog import settle_dialog
from agent.formatting.game_state import format_party_info
from agent.utils import build_screenshot_content
from common.schemas import Coords

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState

type BattleToolResult = list[str | BinaryContent]


def build_battle_tool_result(
    game_state: GameState,
    *,
    action_result: str,
    dialog: str = "",
) -> str:
    """Build the fresh context returned by a battle tool."""
    sections = [action_result]
    if dialog:
        sections.append(f'Battle dialog: "{dialog}"')
    sections.extend(
        (
            format_party_info(game_state),
            format_available_pokeballs(game_state),
            format_battle_info(game_state),
            "Current onscreen text:\n" + game_state.screen.text,
        ),
    )
    return "\n\n".join(section for section in sections if section)


def is_fight_menu_open(game_state: GameState) -> bool:
    """Check if the fight menu is open.

    Args:
        game_state: Current game state to inspect.

    Returns:
        Whether the standard fight menu is visible.
    """
    screen_text = game_state.screen.text.replace(" ", "").replace("\n", "").replace("▶", "")
    return "FIGHTPKMNITEMRUN" in screen_text


def get_cursor_pos_in_fight_menu(game_state: GameState) -> Coords | None:
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


async def complete_battle_action(
    context: AgentContext,
    action_result: str,
) -> BattleToolResult:
    """Advance dialog, refresh state, and build the in-run tool result.

    Args:
        context: Mutable battle-agent dependencies.
        action_result: Description of the completed emulator input.

    Returns:
        Fresh context for the agent's next decision.
    """
    settlement = await settle_dialog(context, battle=True)
    return [
        build_screenshot_content(settlement.screenshot),
        build_battle_tool_result(
            settlement.game_state,
            action_result=action_result,
            dialog=settlement.transcript,
        ),
    ]


async def refresh_battle_observation(
    context: AgentContext,
    *,
    action_result: str,
) -> BattleToolResult:
    """Capture and render a fresh battle observation for the agent."""
    game_state, screenshot = await context.emulator.get_game_state_with_screenshot()
    return [
        build_screenshot_content(screenshot),
        build_battle_tool_result(
            game_state,
            action_result=action_result,
        ),
    ]
