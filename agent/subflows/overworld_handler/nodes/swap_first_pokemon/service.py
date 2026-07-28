"""Business logic for swap first Pokémon in the overworld subflow."""

from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.overworld_handler.nodes.swap_first_pokemon.prompts import (
    SWAP_FIRST_POKEMON_PROMPT,
)
from agent.subflows.overworld_handler.nodes.swap_first_pokemon.schemas import (
    SwapFirstPokemonResponse,
    SwapPokemonError,
)
from common.enums import Button
from llm.service import OpenAILLMService

if TYPE_CHECKING:
    from emulator.emulator import YellowLegacyEmulator
    from memory.rolling_memory import RollingMemory


class SwapFirstPokemonService:
    """A service that swaps the first Pokemon in the party with another Pokemon."""

    llm_service = OpenAILLMService()

    def __init__(
        self,
        rolling_memory: RollingMemory,
        emulator: YellowLegacyEmulator,
    ) -> None:
        """Initialize the swap-first-Pokémon service."""
        self.rolling_memory = rolling_memory
        self.emulator = emulator

    async def swap_first_pokemon(self) -> RollingMemory:
        """Swap the first Pokemon in the party with another Pokemon."""
        try:
            index = await self._get_swap_index()
            await self._swap_first_pokemon(index)
            game_state = await self.emulator.get_game_state()
            self.rolling_memory.add_memory(
                content=(
                    f"I successfully swapped the order of my Pokemon. The new party order is "
                    f"{[p.name for p in game_state.party]}. My lead Pokemon is now "
                    f"{game_state.party[0].name}."
                ),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error in the swap first Pokemon response. Skipping. {e}")
            game_state = await self.emulator.get_game_state()
            self.rolling_memory.add_memory(
                content=(
                    f"An error occurred while swapping the first Pokemon in my party: {e}"
                    f"The current party order is {[p.name for p in game_state.party]}. My lead"
                    f" Pokemon is {game_state.party[0].name}."
                ),
            )
        return self.rolling_memory

    async def _get_swap_index(self) -> int:
        """Get the index of the Pokemon to swap with the first Pokemon."""
        game_state = await self.emulator.get_game_state()
        last_memory = str(self.rolling_memory.current_block)
        prompt = SWAP_FIRST_POKEMON_PROMPT.format(
            thought=last_memory,
            party_info=game_state.party_info,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            messages=prompt,
            schema=SwapFirstPokemonResponse,
        )
        if response.index == 0:
            first_pokemon = game_state.party[0].name
            raise ValueError(f"{first_pokemon} is already the first Pokemon in my party.")
        return response.index

    async def _swap_first_pokemon(self, pokemon_index: int) -> None:
        """Swap the first Pokemon in the party with the Pokemon at the given index."""
        game_state = await self.emulator.get_game_state()
        if game_state.is_text_on_screen():
            raise SwapPokemonError("Can't swap Pokemon in a non-overworld state.")

        # Splitting into sub-steps for easier debugging. Otherwise the various game states become
        # too difficult to keep track of.
        await self._open_start_menu()
        await self._open_pokemon_menu()
        await self._select_pokemon(pokemon_index)
        await self._select_switch_option()
        await self._swap_pokemon()

        # Exit the menu.
        await self.emulator.press_button(Button.B)
        await self.emulator.press_button(Button.B)

    async def _open_start_menu(self) -> None:
        """Open the start menu."""
        await self.emulator.press_button(Button.START)
        game_state = await self.emulator.get_game_state()
        screen_text = game_state.screen.text
        if "POKéDEX" not in screen_text or "POKéMON" not in screen_text:
            raise SwapPokemonError("Failed to open the START menu.")

    async def _open_pokemon_menu(self) -> None:
        """Open the POKéMON menu."""
        game_state = await self.emulator.get_game_state()
        idx_diff = game_state.screen.menu_item_index - 1
        await self._move_cursor(idx_diff)

        screen_text = (await self.emulator.get_game_state()).screen.text
        if "▶POKéMON" not in screen_text:
            raise SwapPokemonError("Failed to open the POKéMON menu.")
        await self.emulator.press_button(Button.A)

        screen_text = (await self.emulator.get_game_state()).screen.text
        if "Choose a POKéMON." not in screen_text:
            raise SwapPokemonError("Failed to open the POKéMON menu.")

    async def _select_pokemon(self, pokemon_index: int) -> None:
        """Move the cursor to the Pokemon at the given index."""
        game_state = await self.emulator.get_game_state()
        idx_diff = game_state.screen.menu_item_index - pokemon_index
        await self._move_cursor(idx_diff)
        await self.emulator.press_button(Button.A)

    async def _select_switch_option(self) -> None:
        """Select the SWITCH option."""
        for _ in range(6):  # Go to the bottom of the menu.
            await self.emulator.press_button(Button.DOWN)
        await self.emulator.press_button(Button.UP)  # Go up to the SWITCH option.

        screen_text = (await self.emulator.get_game_state()).screen.text
        if "▶SWITCH" not in screen_text:
            raise SwapPokemonError("Failed to open the SWITCH menu.")
        await self.emulator.press_button(Button.A)

    async def _swap_pokemon(self) -> None:
        """Swap the Pokemon at position 0 with the Pokemon at position 1."""
        game_state = await self.emulator.get_game_state()
        idx_diff = game_state.screen.menu_item_index - 0
        await self._move_cursor(idx_diff)
        await self.emulator.press_button(Button.A)

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
