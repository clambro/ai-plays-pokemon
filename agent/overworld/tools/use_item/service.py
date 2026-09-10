"""Business logic for the overworld item-use tool."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.utils import move_cursor
from common.constants import ACTION_RESULT_LABEL
from common.enums import Button
from emulator.control_events import ControlHandoff

if TYPE_CHECKING:
    from emulator.emulator import Emulator
    from memory.rolling_memory.schemas import RollingMemory


class UseItemError(Exception):
    """An error that occurs when using an item."""


async def use_item(*, rolling_memory: RollingMemory, emulator: Emulator, item_index: int) -> str:
    """Use the item at the requested inventory index."""
    try:
        item_name = await _use_item(emulator, item_index)
        result = f"I used {item_name} from inventory slot {item_index}."
    except ControlHandoff:
        raise
    except Exception as error:  # noqa: BLE001
        if not isinstance(error, UseItemError):
            logger.exception("Unexpected error while using an inventory item.")
        result = f"I failed to use an item from my inventory. {error}"
    result = f"{ACTION_RESULT_LABEL} {result}"
    rolling_memory.add_memory(result)
    return result


async def _use_item(emulator: Emulator, item_index: int) -> str:
    """Use the item at the given index."""
    game_state = await emulator.get_game_state()
    if item_index >= len(game_state.inventory.items):
        raise UseItemError(f"Inventory slot {item_index} is not available.")
    if game_state.is_text_on_screen():
        raise UseItemError("Can't use an item in a non-overworld state.")
    item_name = game_state.inventory.items[item_index].name

    # Splitting into sub-steps for easier debugging. Otherwise the various game states become
    # too difficult to keep track of.
    await _open_start_menu(emulator)
    await _open_item_menu(emulator)
    await _select_item(emulator, item_index)
    return item_name


async def _open_start_menu(emulator: Emulator) -> None:
    """Open the start menu."""
    await emulator.press_button(Button.START)
    game_state = await emulator.get_game_state()
    screen_text = game_state.screen.text
    if "POKéDEX" not in screen_text and "POKéMON" not in screen_text:
        raise UseItemError("Failed to open the START menu.")


async def _open_item_menu(emulator: Emulator) -> None:
    """Open the ITEM menu."""
    game_state = await emulator.get_game_state()
    item_menu_position = 2
    await move_cursor(emulator, game_state.screen.menu_item_index, item_menu_position)

    screen_text = (await emulator.get_game_state()).screen.text
    if "▶ITEM" not in screen_text:
        raise UseItemError("Failed to open the ITEM menu.")
    await emulator.press_button(Button.A)


async def _select_item(emulator: Emulator, item_index: int) -> None:
    """Move the cursor to the item at the given index."""
    screen = (await emulator.get_game_state()).screen
    await move_cursor(emulator, screen.menu_item_index + screen.list_scroll_offset, item_index)
    await emulator.press_button(Button.A)  # Select the item.
    await emulator.press_button(Button.A)  # Use the item.
