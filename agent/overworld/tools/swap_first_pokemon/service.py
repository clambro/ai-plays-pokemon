"""Business logic for the overworld party-order tool."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.utils import move_cursor
from common.constants import ACTION_RESULT_LABEL
from common.enums import Button
from emulator.control_events import ControlHandoff

if TYPE_CHECKING:
    from emulator.emulator import Emulator
    from memory.rolling_memory.schemas import RollingMemory


class SwapPokemonError(Exception):
    """An error that occurs when swapping a Pokemon."""


async def swap_first_pokemon(
    *, rolling_memory: RollingMemory, emulator: Emulator, pokemon_index: int
) -> str:
    """Swap the first Pokemon with the Pokemon at the requested party index."""
    try:
        await _swap_first_pokemon(emulator, pokemon_index)
        game_state = await emulator.get_game_state()
        result = (
            "I successfully swapped the order of my Pokemon. The new party order is "
            f"{[p.name for p in game_state.party]}."
        )
    except ControlHandoff:
        raise
    except Exception as error:  # noqa: BLE001
        if not isinstance(error, SwapPokemonError):
            logger.exception("Unexpected error while changing the party order.")
        game_state = await emulator.get_game_state()
        result = (
            f"An error occurred while swapping the first Pokemon in my party: {error} "
            f"The current party order is {[p.name for p in game_state.party]}."
        )
    result = f"{ACTION_RESULT_LABEL} {result}"
    rolling_memory.add_memory(result)
    return result


async def _swap_first_pokemon(emulator: Emulator, pokemon_index: int) -> None:
    """Swap the first Pokemon in the party with the Pokemon at the given index."""
    game_state = await emulator.get_game_state()
    if pokemon_index <= 0 or pokemon_index >= len(game_state.party):
        raise SwapPokemonError(f"Party slot {pokemon_index} is not available.")
    if game_state.is_text_on_screen():
        raise SwapPokemonError("Can't swap Pokemon in a non-overworld state.")

    # Splitting into sub-steps for easier debugging. Otherwise the various game states become
    # too difficult to keep track of.
    await _open_start_menu(emulator)
    await _open_pokemon_menu(emulator)
    await _select_pokemon(emulator, pokemon_index)
    await _select_switch_option(emulator)
    await _swap_pokemon(emulator)

    # Exit the menu.
    await emulator.press_button(Button.B)
    await emulator.press_button(Button.B)


async def _open_start_menu(emulator: Emulator) -> None:
    """Open the start menu."""
    await emulator.press_button(Button.START)
    game_state = await emulator.get_game_state()
    screen_text = game_state.screen.text
    if "POKéDEX" not in screen_text or "POKéMON" not in screen_text:
        raise SwapPokemonError("Failed to open the START menu.")


async def _open_pokemon_menu(emulator: Emulator) -> None:
    """Open the POKéMON menu."""
    game_state = await emulator.get_game_state()
    await move_cursor(emulator, game_state.screen.menu_item_index, 1)

    screen_text = (await emulator.get_game_state()).screen.text
    if "▶POKéMON" not in screen_text:
        raise SwapPokemonError("Failed to open the POKéMON menu.")
    await emulator.press_button(Button.A)

    screen_text = (await emulator.get_game_state()).screen.text
    if "Choose a POKéMON." not in screen_text:
        raise SwapPokemonError("Failed to open the POKéMON menu.")


async def _select_pokemon(emulator: Emulator, pokemon_index: int) -> None:
    """Move the cursor to the Pokemon at the given index."""
    game_state = await emulator.get_game_state()
    await move_cursor(emulator, game_state.screen.menu_item_index, pokemon_index)
    await emulator.press_button(Button.A)


async def _select_switch_option(emulator: Emulator) -> None:
    """Select the SWITCH option."""
    for _ in range(6):  # Go to the bottom of the menu.
        await emulator.press_button(Button.DOWN)
    await emulator.press_button(Button.UP)  # Go up to the SWITCH option.

    screen_text = (await emulator.get_game_state()).screen.text
    if "▶SWITCH" not in screen_text:
        raise SwapPokemonError("Failed to open the SWITCH menu.")
    await emulator.press_button(Button.A)


async def _swap_pokemon(emulator: Emulator) -> None:
    """Swap the Pokemon at position 0 with the Pokemon at position 1."""
    game_state = await emulator.get_game_state()
    await move_cursor(emulator, game_state.screen.menu_item_index, 0)
    await emulator.press_button(Button.A)
