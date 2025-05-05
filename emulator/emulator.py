import asyncio
from pathlib import Path
from contextlib import AbstractAsyncContextManager

from pyboy import PyBoy
from common.constants import GAME_TICKS_PER_SECOND
from emulator.game_state import YellowLegacyGameState
from PIL.Image import Image


class YellowLegacyEmulator(AbstractAsyncContextManager):
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
        self._tick_task: asyncio.Task | None = None

    async def __aenter__(self) -> "YellowLegacyEmulator":
        """Start the emulator's tick task when entering the context."""
        self._tick_task = asyncio.create_task(self.async_tick_indefinitely())
        await asyncio.sleep(1)  # Give the emulator a few ticks to load before continuing
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Stop the emulator and cancel the tick task when exiting the context."""
        self.stop()
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass

    def get_game_state(self) -> YellowLegacyGameState:
        """
        Get the current game state, lazily updating it if necessary.

        :return: The current game state.
        """
        self._check_stopped()
        if self.tick_num != self._game_state.tick_num:
            self._game_state = YellowLegacyGameState.from_memory(self._pyboy.memory, self.tick_num)
        return self._game_state

    def _tick(self, count: int = 1) -> bool:
        """
        Tick the emulator forward by `count` frames.

        :param count: Number of frames to tick forward.
        :return: Whether the game is still running.
        """
        self._check_stopped()
        self.tick_num += count
        return self._pyboy.tick(count, render=True, sound=True)

    async def async_tick_indefinitely(self) -> None:
        """Tick the emulator indefinitely. Should be run on its own thread."""
        while True:
            self._check_stopped()
            if not self._tick():
                self.stop()
                break
            await asyncio.sleep(0)  # Return control to the event loop.

    def stop(self) -> None:
        """Stop the emulator."""
        self._is_stopped = True
        self._pyboy.stop()

    def get_screenshot(self) -> Image:
        """Get a screenshot of the current game screen."""
        self._check_stopped()
        img = self._pyboy.screen.image
        if not isinstance(img, Image):
            raise RuntimeError("No screenshot available")
        return img

    async def press_buttons(self, buttons: list[str], delay_frames: int = 10) -> None:
        """Press the buttons in order, with a delay between each."""
        self._check_stopped()
        for button in buttons:
            self._pyboy.button(button, delay_frames)
            await asyncio.sleep(delay_frames / GAME_TICKS_PER_SECOND)

    def _check_stopped(self) -> None:
        if self._is_stopped:
            raise RuntimeError("Emulator is stopped")
