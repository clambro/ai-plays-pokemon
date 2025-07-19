from loguru import logger

from agent.subflows.overworld_handler.nodes.use_item.prompts import USE_ITEM_PROMPT
from agent.subflows.overworld_handler.nodes.use_item.schemas import UseItemError, UseItemResponse
from common.enums import Button
from emulator.emulator import YellowLegacyEmulator
from llm.schemas import GEMINI_FLASH_LITE_2_5
from llm.service import GeminiLLMService
from memory.raw_memory import RawMemory


class UseItemService:
    """A service that uses an item from the inventory."""

    llm_service = GeminiLLMService(GEMINI_FLASH_LITE_2_5)

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.emulator = emulator

    async def use_item(self) -> RawMemory:
        """Use an item from the inventory."""
        try:
            index = await self._get_item_index()
            await self._use_item(index)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error in the use item response. Skipping. {e}")
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=f"I failed to use an item from my inventory. {e}",
            )
        return self.raw_memory

    async def _get_item_index(self) -> int:
        """Get the index of the item to use."""
        game_state = self.emulator.get_game_state()
        last_memory = self.raw_memory.pieces[self.iteration]
        inventory_str = "\n".join(
            f"[{i}] {item.name}" for i, item in enumerate(game_state.inventory.items)
        )
        prompt = USE_ITEM_PROMPT.format(thought=last_memory, inventory=inventory_str)
        response = await self.llm_service.get_llm_response_pydantic(
            messages=prompt,
            schema=UseItemResponse,
            prompt_name="get_item_index",
        )
        return response.index

    async def _use_item(self, item_index: int) -> None:
        """Use the item at the given index."""
        game_state = self.emulator.get_game_state()
        if game_state.is_text_on_screen():
            raise UseItemError("Can't use an item in a non-overworld state.")

        # Splitting into sub-steps for easier debugging. Otherwise the various game states become
        # too difficult to keep track of.
        await self._open_start_menu()
        await self._open_item_menu()
        await self._select_item(item_index)

    async def _open_start_menu(self) -> None:
        """Open the start menu."""
        await self.emulator.press_button(Button.START)
        game_state = self.emulator.get_game_state()
        screen_text = game_state.screen.text
        if "POKéDEX" not in screen_text and "POKéMON" not in screen_text:
            raise UseItemError("Failed to open the START menu.")

    async def _open_item_menu(self) -> None:
        """Open the ITEM menu."""
        game_state = self.emulator.get_game_state()
        idx_diff = game_state.screen.menu_item_index - 1
        await self._move_cursor(idx_diff)

        screen_text = self.emulator.get_game_state().screen.text
        if "▶ITEM" not in screen_text:
            raise UseItemError("Failed to open the ITEM menu.")
        await self.emulator.press_button(Button.A)

    async def _select_item(self, item_index: int) -> None:
        """Move the cursor to the item at the given index."""
        screen = self.emulator.get_game_state().screen
        idx_diff = screen.menu_item_index + screen.list_scroll_offset - item_index
        await self._move_cursor(idx_diff)
        await self.emulator.press_button(Button.A)  # Select the item.
        await self.emulator.press_button(Button.A)  # Use the item.

    async def _move_cursor(self, step: int) -> None:
        """
        Move the cursor up by the given number of steps. Positive steps move the cursor up; negative
        steps move the cursor down.
        """
        if step > 0:
            for _ in range(step):
                await self.emulator.press_button(Button.UP)
        elif step < 0:
            for _ in range(-step):
                await self.emulator.press_button(Button.DOWN)
