from loguru import logger

from agent.subflows.overworld_handler.nodes.swap_first_pokemon.prompts import (
    SWAP_FIRST_POKEMON_PROMPT,
)
from agent.subflows.overworld_handler.nodes.swap_first_pokemon.schemas import (
    SwapFirstPokemonResponse,
    SwapPokemonError,
)
from common.enums import Button
from emulator.emulator import YellowLegacyEmulator
from llm.schemas import GEMINI_FLASH_LITE_2_5
from llm.service import GeminiLLMService
from memory.raw_memory import RawMemory


class SwapFirstPokemonService:
    """A service that swaps the first Pokemon in the party with another Pokemon."""

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

    async def swap_first_pokemon(self) -> RawMemory:
        """Swap the first Pokemon in the party with another Pokemon."""
        try:
            index = await self._get_swap_index()
            await self._swap_first_pokemon(index)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error in the swap first Pokemon response. Skipping. {e}")
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=f"I failed to swap the first Pokemon in my party with another Pokemon. {e}",
            )
            return self.raw_memory

        self.raw_memory.add_memory(
            iteration=self.iteration,
            content="I successfully swapped the first Pokemon in my party with another Pokemon.",
        )
        return self.raw_memory

    async def _get_swap_index(self) -> int:
        """Get the index of the Pokemon to swap with the first Pokemon."""
        last_memory = self.raw_memory.pieces.get(self.iteration) or ""
        prompt = SWAP_FIRST_POKEMON_PROMPT.format(last_memory=last_memory)
        response = await self.llm_service.get_llm_response_pydantic(
            messages=prompt,
            schema=SwapFirstPokemonResponse,
            prompt_name="swap_first_pokemon",
        )
        return response.index

    async def _swap_first_pokemon(self, pokemon_index: int) -> None:
        """Swap the first Pokemon in the party with the Pokemon at the given index."""
        game_state = self.emulator.get_game_state()
        if game_state.is_text_on_screen():
            raise SwapPokemonError("Can't swap Pokemon in a non-overworld state.")

        # Open the start menu.
        await self.emulator.press_button(Button.START)
        game_state = self.emulator.get_game_state()
        screen_text = game_state.screen.text
        if "POKéDEX" not in screen_text and "POKéMON" not in screen_text:
            raise SwapPokemonError("Failed to open the START menu.")

        # Open the POKéMON menu.
        idx_diff = game_state.screen.menu_item_index - 1
        await self._move_cursor(idx_diff)
        if "▶POKéMON" not in screen_text:
            raise SwapPokemonError("Failed to open the POKéMON menu.")
        await self.emulator.press_button(Button.A)
        game_state = self.emulator.get_game_state()
        if "Choose a POKéMON." not in game_state.screen.text:
            raise SwapPokemonError("Failed to open the POKéMON menu.")

        # Move the cursor to the Pokemon.
        idx_diff = game_state.screen.menu_item_index - pokemon_index
        await self._move_cursor(idx_diff)
        await self.emulator.press_button(Button.A)

        # Select the SWITCH option.
        for _ in range(5):
            await self.emulator.press_button(Button.DOWN)  # Go to the bottom of the menu.
        await self.emulator.press_button(Button.UP)  # Go up to the SWITCH option.
        game_state = self.emulator.get_game_state()
        if "▶SWITCH" not in screen_text:
            raise SwapPokemonError("Failed to open the SWITCH menu.")
        await self.emulator.press_button(Button.A)

        # Move the cursor to position 0 and swap.
        idx_diff = game_state.screen.menu_item_index - 0
        await self._move_cursor(idx_diff)
        await self.emulator.press_button(Button.A)

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
