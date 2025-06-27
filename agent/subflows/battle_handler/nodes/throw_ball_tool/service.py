from loguru import logger

from agent.subflows.battle_handler.schemas import ThrowBallToolArgs
from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from memory.raw_memory import RawMemory, RawMemoryPiece


class ThrowBallToolService:
    """A service that throws a ball at the enemy."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        tool_args: ThrowBallToolArgs,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.tool_args = tool_args
        self.emulator = emulator

    async def throw_ball(self) -> RawMemory:
        """Throw a ball at the enemy."""
        game_state = self.emulator.get_game_state()
        cursor_pos = get_cursor_pos_in_fight_menu(game_state)
        if cursor_pos is None:
            logger.warning("The fight menu is not open. Skipping.")
            return self.raw_memory

        # Open the ITEM menu and update the game state.
        if cursor_pos.col == 1:
            await self.emulator.press_button(Button.LEFT)
        if cursor_pos.row == 0:
            await self.emulator.press_button(Button.DOWN)
        await self.emulator.press_button(Button.A)
        game_state = self.emulator.get_game_state()

        cursor_index = self._get_item_menu_cursor_index(game_state)
        if cursor_index is None:
            logger.warning("The item menu is not open. Skipping.")
            return self.raw_memory

        # Throw the ball.
        idx_diff = cursor_index - self.tool_args.item_index
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
                content=f"Attempted to throw a {self.tool_args.ball}.",
            ),
        )
        return self.raw_memory

    @staticmethod
    def _get_item_menu_cursor_index(game_state: YellowLegacyGameState) -> int | None:
        """Get the cursor index in the item menu."""
        dialog_box = game_state.get_dialog_box()
        if dialog_box is None:
            return None

        dialog_text = dialog_box.top_line + dialog_box.bottom_line
        idx = game_state.screen.menu_item_index + game_state.screen.list_scroll_offset
        if dialog_text or idx >= len(game_state.inventory.items):
            return None  # Item menu is not open.
        return idx
