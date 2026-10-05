"""Select Pokemon through the PC's scrolling lists."""

from typing import TYPE_CHECKING

from agent.text.tools.errors import TextActionUnavailableError
from agent.utils import move_cursor
from common.enums import Button, PokemonListSource

if TYPE_CHECKING:
    from emulator.emulator import Emulator


async def select_pc_pokemon(*, emulator: Emulator, pokemon_index: int) -> str:
    """Select a PC list entry without confirming a transfer or release.

    Args:
        emulator: Running emulator with a PC Pokemon list open.
        pokemon_index: Zero-based index in the displayed party or active box.

    Returns:
        Confirmation of the selected Pokemon.

    Raises:
        TextActionUnavailableError: No PC Pokemon list is open or the index is invalid.
    """
    game_state = await emulator.get_game_state()
    match game_state.screen.pokemon_list_source:
        case PokemonListSource.PARTY:
            pokemon = game_state.party
        case PokemonListSource.BOX:
            pokemon = game_state.pc_pokemon
        case None:
            raise TextActionUnavailableError("The PC Pokemon selection list is not open.")
    if not 0 <= pokemon_index < len(pokemon):
        raise TextActionUnavailableError(f"Pokemon index {pokemon_index} is not in this PC list.")

    cursor_index = game_state.screen.menu_item_index + game_state.screen.list_scroll_offset
    await move_cursor(emulator, cursor_index, pokemon_index)
    await emulator.press_button(Button.A)
    return f"Selected {pokemon[pokemon_index].name} from PC list index {pokemon_index}."
