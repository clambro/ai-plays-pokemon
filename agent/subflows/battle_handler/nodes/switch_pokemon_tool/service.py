from loguru import logger

from agent.subflows.battle_handler.schemas import SwitchPokemonToolArgs
from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from memory.raw_memory import RawMemory, RawMemoryPiece


class SwitchPokemonToolService:
    """A service that switches to a different Pokemon."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        tool_args: SwitchPokemonToolArgs,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.tool_args = tool_args
        self.emulator = emulator

    async def switch_pokemon(self) -> RawMemory:
        """Switch to a different Pokemon."""
        game_state = self.emulator.get_game_state()
        cursor_pos = get_cursor_pos_in_fight_menu(game_state)
        if cursor_pos is None:
            logger.warning("The fight menu is not open. Skipping.")
            return self.raw_memory

        # Open the PKMN menu and update the game state.
        if cursor_pos.col == 0:
            await self.emulator.press_button(Button.RIGHT)
        if cursor_pos.row == 1:
            await self.emulator.press_button(Button.UP)
        await self.emulator.press_button(Button.A)
        game_state = self.emulator.get_game_state()

        cursor_index = self._get_pkmn_menu_cursor_index(game_state)
        if cursor_index is None:
            logger.warning("The Pokemon menu is not open. Skipping.")
            return self.raw_memory

        # Move the cursor to the Pokemon and update the game state.
        idx_diff = cursor_index - self.tool_args.party_index
        if idx_diff > 0:
            for _ in range(idx_diff):
                await self.emulator.press_button(Button.UP)
        elif idx_diff < 0:
            for _ in range(-idx_diff):
                await self.emulator.press_button(Button.DOWN)
        await self.emulator.press_button(Button.A)
        game_state = self.emulator.get_game_state()

        cursor_index = self._get_switch_menu_cursor_index(game_state)
        if cursor_index is None:
            logger.warning("The switch menu is not open. Skipping.")
            return self.raw_memory

        # Select the Pokemon.
        for _ in range(cursor_index):
            await self.emulator.press_button(Button.UP)
        await self.emulator.press_button(Button.A, wait_for_animation=False)

        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=f"Attempted to to switch to {self.tool_args.name}.",
            ),
        )
        return self.raw_memory

    @staticmethod
    def _get_pkmn_menu_cursor_index(game_state: YellowLegacyGameState) -> int | None:
        """Get the cursor index in the Pokemon menu."""
        menu_idx = game_state.screen.menu_item_index
        if "Choose a POKéMON." not in game_state.screen.text or menu_idx >= len(game_state.party):
            return None
        return menu_idx

    @staticmethod
    def _get_switch_menu_cursor_index(game_state: YellowLegacyGameState) -> int | None:
        """Get the cursor index in the switch menu."""
        text = game_state.screen.text
        if "▶SWITCH" in text:
            return 0
        if "▶STATS" in text:
            return 1
        if "▶CANCEL" in text:
            return 2
        return None


_CURSOR_POS_TO_ROW_MAP = {  # Very unusual pattern...
    180: 0,
    220: 1,
    4: 2,
    44: 3,
    84: 4,
    124: 5,
}
