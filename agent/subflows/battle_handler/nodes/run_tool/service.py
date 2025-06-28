from loguru import logger

from agent.subflows.battle_handler.utils import get_cursor_pos_in_fight_menu
from common.enums import Button
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory


class RunToolService:
    """A service that runs away from the battle."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.emulator = emulator

    async def run_away(self) -> RawMemory:
        """Run away from the battle."""
        game_state = self.emulator.get_game_state()
        cursor_pos = get_cursor_pos_in_fight_menu(game_state)
        if cursor_pos is None:
            logger.warning("The fight menu is not open. Skipping.")
            return self.raw_memory

        if cursor_pos.col == 0:
            await self.emulator.press_button(Button.RIGHT)
        if cursor_pos.row == 0:
            await self.emulator.press_button(Button.DOWN)
        await self.emulator.press_button(Button.A, wait_for_animation=False)

        self.raw_memory.add_memory(
            iteration=self.iteration,
            content="Attempted to run away from the battle.",
        )
        return self.raw_memory
