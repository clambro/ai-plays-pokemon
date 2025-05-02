import asyncio
from pathlib import Path

from pyboy import PyBoy
from constants import GAME_TICKS_PER_SECOND
from emulator.game_state import YellowLegacyGameState


class YellowLegacyEmulator:
    """
    Wrapper for accessing the game state of Pokemon Yellow Legacy. Encapsulates the PyBoy API so
    that the rest of the codebase doesn't need to worry about emulation or memory addresses.
    """

    def __init__(self, rom_path: str, initial_state_path: str | None = None) -> None:
        self.tick_num = 0
        self.pyboy = PyBoy(rom_path)
        if initial_state_path:
            with Path(initial_state_path).open("rb") as f:
                self.pyboy.load_state(f)

        self._game_state = YellowLegacyGameState.from_memory(self.pyboy.memory, self.tick_num)

    @property
    def game_state(self) -> YellowLegacyGameState:
        """
        Get the current game state, lazily updating it if necessary.

        :return: The current game state.
        """
        if self.tick_num != self._game_state.tick_num:
            self._game_state = YellowLegacyGameState.from_memory(self.pyboy.memory, self.tick_num)
        return self._game_state

    def tick(self, count: int = 1) -> bool:
        """
        Tick the emulator forward by `count` frames.

        :param count: Number of frames to tick forward.
        :return: Whether the game is still running.
        """
        self.tick_num += count
        return self.pyboy.tick(count, render=True, sound=True)

    def stop(self) -> None:
        """Stop the emulator."""
        self.pyboy.stop()

    def take_screenshot(self) -> bytes:
        """Take a screenshot of the current game state."""
        img = self.pyboy.screen.image
        if img is None:
            raise RuntimeError("No screenshot available")
        return img.tobytes()

    async def press_buttons(self, buttons: list[str], delay_frames: int = 10) -> None:
        """Press the buttons in order, with a delay between each."""
        for button in buttons:
            self.pyboy.button(button, delay_frames)
            await asyncio.sleep(delay_frames / GAME_TICKS_PER_SECOND)
