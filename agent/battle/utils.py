"""Gameplay predicates and menu recognition for battles."""

from typing import TYPE_CHECKING

from common.enums import EvolutionFamily
from common.schemas import Coords

if TYPE_CHECKING:
    from emulator.game_state import GameState


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


def is_evolution_family_caught(
    pokedex_number: int,
    caught_pokedex_numbers: frozenset[int],
) -> bool:
    """Return whether a related Pokemon has already been caught."""
    group = next(
        (group.value for group in EvolutionFamily if pokedex_number in group.value),
        (pokedex_number,),
    )
    return any(member in caught_pokedex_numbers for member in group)
