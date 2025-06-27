from loguru import logger

from agent.subflows.battle_handler.schemas import FightToolArgs
from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from memory.raw_memory import RawMemory, RawMemoryPiece


class FightToolService:
    """A service that uses a move on the enemy."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        tool_args: FightToolArgs,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.tool_args = tool_args
        self.emulator = emulator

    async def fight(self) -> RawMemory:
        """Use a move on the enemy."""
        game_state = self.emulator.get_game_state()
        cursor_pos = get_cursor_pos_in_fight_menu(game_state)
        if cursor_pos is None:
            logger.warning("The fight menu is not open. Skipping.")
            return self.raw_memory

        # Open the FIGHT menu and update the game state.
        if cursor_pos.col == 1:
            await self.emulator.press_button(Button.LEFT)
        if cursor_pos.row == 1:
            await self.emulator.press_button(Button.UP)
        await self.emulator.press_button(Button.A)
        game_state = self.emulator.get_game_state()

        cursor_index = self._get_move_menu_cursor_index(game_state)
        if cursor_index is None:
            logger.warning("The move menu is not open. Skipping.")
            return self.raw_memory

        # Use the move.
        idx_diff = cursor_index - self.tool_args.move_index
        if idx_diff > 0:
            for _ in range(idx_diff):
                await self.emulator.press_button(Button.UP)
        elif idx_diff < 0:
            for _ in range(-idx_diff):
                await self.emulator.press_button(Button.DOWN)
        await self.emulator.press_button(Button.A, wait_for_animation=False)

        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=f"Attempted to to use {self.tool_args.move_name}.",
            ),
        )
        return self.raw_memory

    @staticmethod
    def _get_move_menu_cursor_index(game_state: YellowLegacyGameState) -> int | None:
        """Get the cursor index in the move menu."""
        text = game_state.screen.text
        if text.split("\n")[9][1:6] != "TYPE/":
            return None  # Move menu is not open because the type of the move is not shown.
        if game_state.battle.player_pokemon is None:
            return None  # No active Pokemon. Shouldn't happen.

        for i, move in enumerate(game_state.battle.player_pokemon.moves):
            if f"▶{move.name}" in text:
                return i
        return None
