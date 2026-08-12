"""Business logic for the overworld item-use tool."""

from typing import TYPE_CHECKING

from loguru import logger

from common.enums import Button

if TYPE_CHECKING:
    from emulator.emulator import Emulator
    from memory.rolling_memory.schemas import RollingMemory


class UseItemError(Exception):
    """An error that occurs when using an item."""


class UseItemService:
    """A service that uses an item from the inventory."""

    def __init__(
        self,
        rolling_memory: RollingMemory,
        emulator: Emulator,
    ) -> None:
        """Initialize the use item service."""
        self.rolling_memory = rolling_memory
        self.emulator = emulator

    async def use_item(self, item_index: int) -> str:
        """Use the item at the requested inventory index."""
        try:
            item_name = await self._use_item(item_index)
            result = f"Used {item_name} from inventory slot {item_index}."
        except Exception as error:  # noqa: BLE001
            if not isinstance(error, UseItemError):
                logger.exception("Unexpected error while using an inventory item.")
            result = f"Failed to use an inventory item: {error}"
        self.rolling_memory.add_memory(result)
        return result

    async def _use_item(self, item_index: int) -> str:
        """Use the item at the given index."""
        game_state = await self.emulator.get_game_state()
        if item_index >= len(game_state.inventory.items):
            raise UseItemError(f"Inventory slot {item_index} is not available.")
        if game_state.is_text_on_screen():
            raise UseItemError("Can't use an item in a non-overworld state.")
        item_name = game_state.inventory.items[item_index].name

        # Splitting into sub-steps for easier debugging. Otherwise the various game states become
        # too difficult to keep track of.
        await self._open_start_menu()
        await self._open_item_menu()
        await self._select_item(item_index)
        return item_name

    async def _open_start_menu(self) -> None:
        """Open the start menu."""
        await self.emulator.press_button(Button.START)
        game_state = await self.emulator.get_game_state()
        screen_text = game_state.screen.text
        if "POKéDEX" not in screen_text and "POKéMON" not in screen_text:
            raise UseItemError("Failed to open the START menu.")

    async def _open_item_menu(self) -> None:
        """Open the ITEM menu."""
        game_state = await self.emulator.get_game_state()
        item_menu_position = 2
        idx_diff = game_state.screen.menu_item_index - item_menu_position
        await self._move_cursor(idx_diff)

        screen_text = (await self.emulator.get_game_state()).screen.text
        if "▶ITEM" not in screen_text:
            raise UseItemError("Failed to open the ITEM menu.")
        await self.emulator.press_button(Button.A)

    async def _select_item(self, item_index: int) -> None:
        """Move the cursor to the item at the given index."""
        screen = (await self.emulator.get_game_state()).screen
        idx_diff = screen.menu_item_index + screen.list_scroll_offset - item_index
        await self._move_cursor(idx_diff)
        await self.emulator.press_button(Button.A)  # Select the item.
        await self.emulator.press_button(Button.A)  # Use the item.

    async def _move_cursor(self, step: int) -> None:
        """Move a vertical menu cursor by a signed number of steps.

        Positive values move up; negative values move down.
        """
        if step > 0:
            for _ in range(step):
                await self.emulator.press_button(Button.UP)
        elif step < 0:
            for _ in range(-step):
                await self.emulator.press_button(Button.DOWN)
