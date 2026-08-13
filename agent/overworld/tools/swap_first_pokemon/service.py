"""Business logic for the overworld party-order tool."""

from typing import TYPE_CHECKING

from loguru import logger

from common.enums import Button

if TYPE_CHECKING:
    from emulator.emulator import Emulator
    from memory.rolling_memory.schemas import RollingMemory


class SwapPokemonError(Exception):
    """An error that occurs when swapping a Pokemon."""


class SwapFirstPokemonService:
    """A service that swaps the first Pokemon in the party with another Pokemon."""

    def __init__(
        self,
        rolling_memory: RollingMemory,
        emulator: Emulator,
    ) -> None:
        """Initialize the swap-first-Pokémon service."""
        self.rolling_memory = rolling_memory
        self.emulator = emulator

    async def swap_first_pokemon(self, pokemon_index: int) -> str:
        """Swap the first Pokemon with the Pokemon at the requested party index."""
        try:
            await self._swap_first_pokemon(pokemon_index)
            game_state = await self.emulator.get_game_state()
            result = (
                "I successfully swapped the order of my Pokemon. The new party order is "
                f"{[p.name for p in game_state.party]}. My lead Pokemon is now "
                f"{game_state.party[0].name}."
            )
        except Exception as error:  # noqa: BLE001
            if not isinstance(error, SwapPokemonError):
                logger.exception("Unexpected error while changing the party order.")
            game_state = await self.emulator.get_game_state()
            result = (
                f"An error occurred while swapping the first Pokemon in my party: {error} "
                f"The current party order is {[p.name for p in game_state.party]}. My lead"
                f" Pokemon is {game_state.party[0].name}."
            )
        self.rolling_memory.add_memory(result)
        return result

    async def _swap_first_pokemon(self, pokemon_index: int) -> None:
        """Swap the first Pokemon in the party with the Pokemon at the given index."""
        game_state = await self.emulator.get_game_state()
        if pokemon_index <= 0 or pokemon_index >= len(game_state.party):
            raise SwapPokemonError(f"Party slot {pokemon_index} is not available.")
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
