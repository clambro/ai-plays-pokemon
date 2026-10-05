"""Shared item selection from the overworld or an open bag."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.utils import move_cursor
from common.enums import Button
from emulator.control_events import ControlHandoff

if TYPE_CHECKING:
    from emulator.emulator import Emulator


class UseItemError(Exception):
    """The requested item cannot be selected from the current state."""


async def use_item(*, emulator: Emulator, item_index: int) -> str:
    """Select an inventory item and choose USE, leaving any further decisions to the agent.

    Args:
        emulator: Running emulator in the overworld or an open bag.
        item_index: Zero-based inventory index.

    Returns:
        The selection result, including a recoverable failure if the item cannot be used.

    Raises:
        ControlHandoff: Control moved to another handler before selection finished.
    """
    try:
        item_name = await _use_item(emulator, item_index)
    except ControlHandoff:
        raise
    except Exception as error:  # noqa: BLE001
        if not isinstance(error, UseItemError):
            logger.exception("Unexpected error while using an inventory item.")
        return f"I failed to use an item from my inventory. {error}"
    else:
        return f"Selected {item_name} from inventory slot {item_index} for use."


async def _use_item(emulator: Emulator, item_index: int) -> str:
    """Validate the current screen and select the requested item."""
    game_state = await emulator.get_game_state()
    if not 0 <= item_index < len(game_state.inventory.items):
        raise UseItemError(f"Inventory slot {item_index} is not available.")
    if game_state.battle.is_in_battle:
        raise UseItemError("Can't use an overworld item during battle.")
    item_name = game_state.inventory.items[item_index].name
    if not game_state.screen.is_bag_menu:
        if game_state.is_text_on_screen():
            raise UseItemError("The bag is not open.")
        await _open_start_menu(emulator)
        await _open_item_menu(emulator)

    screen = (await emulator.get_game_state()).screen
    if not screen.is_bag_menu:
        raise UseItemError("The bag is not open.")
    await move_cursor(emulator, screen.menu_item_index + screen.list_scroll_offset, item_index)
    await emulator.press_button(Button.A)  # Select the item.
    if "▶USE" not in (await emulator.get_game_state()).screen.text:
        raise UseItemError("The selected item does not have a USE option.")
    await emulator.press_button(Button.A)  # Choose USE.
    return item_name


async def _open_start_menu(emulator: Emulator) -> None:
    """Open the start menu."""
    await emulator.press_button(Button.START)
    screen_text = (await emulator.get_game_state()).screen.text
    if "POKéDEX" not in screen_text and "POKéMON" not in screen_text:
        raise UseItemError("Failed to open the START menu.")


async def _open_item_menu(emulator: Emulator) -> None:
    """Open ITEM from the start menu."""
    screen = (await emulator.get_game_state()).screen
    await move_cursor(emulator, screen.menu_item_index, 2)
    if "▶ITEM" not in (await emulator.get_game_state()).screen.text:
        raise UseItemError("Failed to open the ITEM menu.")
    await emulator.press_button(Button.A)
