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
        """Initialize the emulator."""
        self.tick_num = 0
        self._pyboy = PyBoy(rom_path)
        if initial_state_path:
            with Path(initial_state_path).open("rb") as f:
                self._pyboy.load_state(f)
        self._game_state = YellowLegacyGameState.from_memory(self._pyboy.memory, self.tick_num)
        self._is_stopped = False

    def get_game_state(self) -> YellowLegacyGameState:
        """
        Get the current game state, lazily updating it if necessary.

        :return: The current game state.
        """
        self._check_stopped()
        if self.tick_num != self._game_state.tick_num:
            self._game_state = YellowLegacyGameState.from_memory(self._pyboy.memory, self.tick_num)
        return self._game_state

    def tick(self, count: int = 1) -> bool:
        """
        Tick the emulator forward by `count` frames.

        :param count: Number of frames to tick forward.
        :return: Whether the game is still running.
        """
        self._check_stopped()
        self.tick_num += count
        return self._pyboy.tick(count, render=True, sound=True)

    async def async_tick_indefinitely(self) -> None:
        """Tick the emulator indefinitely on its own thread."""
        while True:
            self._check_stopped()
            if not self.tick():
                self.stop()
                break
            await asyncio.sleep(0)  # Return control to the event loop.

    def stop(self) -> None:
        """Stop the emulator."""
        self._is_stopped = True
        self._pyboy.stop()

    def get_screenshot_bytes(self) -> bytes:
        """Get a screenshot of the current game screen as a bytes object."""
        self._check_stopped()
        img = self._pyboy.screen.image
        if img is None:
            raise RuntimeError("No screenshot available")
        return img.tobytes()

    async def press_buttons(self, buttons: list[str], delay_frames: int = 20) -> None:
        """Press the buttons in order, with a delay between each."""
        self._check_stopped()
        for button in buttons:
            self._pyboy.button(button, delay_frames)
            await asyncio.sleep(delay_frames / GAME_TICKS_PER_SECOND)

    def _check_stopped(self) -> None:
        if self._is_stopped:
            raise RuntimeError("Emulator is stopped")
