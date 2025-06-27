from common.schemas import Coords
from emulator.game_state import YellowLegacyGameState


def is_fight_menu_open(game_state: YellowLegacyGameState) -> bool:
    """
    Check if the fight menu is open.

    :param game_state: The game state.
    :return: True if the fight menu is open, False otherwise.
    """
    screen_text = game_state.screen.text.replace(" ", "").replace("\n", "")
    return "FIGHTPKMNITEMRUN" in screen_text


def get_cursor_pos_in_fight_menu(game_state: YellowLegacyGameState) -> Coords | None:
    """
    Get the cursor position in the fight menu.

    :param game_state: The game state.
    :return: The cursor position.
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
