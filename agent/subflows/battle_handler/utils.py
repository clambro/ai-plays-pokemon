"""Shared utilities for the battle subflow."""

from typing import TYPE_CHECKING

from common.schemas import Coords

if TYPE_CHECKING:
    from emulator.game_state import YellowLegacyGameState


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
