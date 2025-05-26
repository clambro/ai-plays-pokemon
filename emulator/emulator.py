import asyncio
from contextlib import AbstractAsyncContextManager
from copy import deepcopy
from pathlib import Path

from loguru import logger
from PIL import Image
from pyboy import PyBoy

from common.constants import GAME_TICKS_PER_SECOND
from common.exceptions import EmulatorIsStoppedError
from emulator.game_state import YellowLegacyGameState


class YellowLegacyEmulator(AbstractAsyncContextManager):
    """
    Wrapper for accessing the game state of Pokemon Yellow Legacy. Encapsulates the PyBoy API so
    that the rest of the codebase doesn't need to worry about emulation or memory addresses.
    """

    def __init__(
        self,
        rom_path: str,
        initial_state_path: str | None = None,
        mute_sound: bool = False,
    ) -> None:
        """Initialize the emulator."""
        self.tick_num = 0
        self._pyboy = PyBoy(rom_path, sound_volume=0 if mute_sound else 100)
        if initial_state_path:
            with Path(initial_state_path).open("rb") as f:
                self._pyboy.load_state(f)
        self._is_stopped = True
        self._tick_task: asyncio.Task | None = None
        self._button_lock = asyncio.Lock()

    async def __aenter__(self) -> "YellowLegacyEmulator":
        """Start the emulator's tick task when entering the context."""
        self._is_stopped = False
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
        """Get the current game state."""
        self._check_stopped()
        return YellowLegacyGameState.from_memory(self._pyboy.memory, self.tick_num)

    async def async_tick_indefinitely(self) -> None:
        """Tick the emulator indefinitely. Should be run on its own thread."""
        while True:
            self._check_stopped()
            async with self._button_lock:
                if not self._tick():
                    self.stop()
                    break
            await asyncio.sleep(0)  # Return control to the event loop

    def stop(self) -> None:
        """Stop the emulator."""
        self._is_stopped = True
        self._pyboy.stop()

    async def get_screenshot(self) -> Image.Image:
        """Asynchronously get a screenshot of the current game screen."""
        self._check_stopped()
        img = deepcopy(self._pyboy.screen.image)
        if not isinstance(img, Image.Image):
            raise RuntimeError("No screenshot available")
        img = await asyncio.to_thread(
            img.resize,
            (img.width * 2, img.height * 2),
            resample=Image.Resampling.NEAREST,
        )
        return img

    async def press_buttons(self, buttons: list[str], delay_frames: int = 10) -> None:
        """Press the buttons in order, with a delay between each."""
        self._check_stopped()
        for button in buttons:
            async with self._button_lock:
                await asyncio.to_thread(self._pyboy.button, button, delay_frames)
            await asyncio.sleep(delay_frames / GAME_TICKS_PER_SECOND)

    async def wait_for_animation_to_finish(self) -> None:
        """Wait until all ongoing animations have finished."""
        logger.info("Checking for animations and waiting for them to finish.")
        successes = 0
        game_state = self.get_game_state()
        while successes < 5:
            new_game_state = self.get_game_state()
            # The blinking cursor should not block progress, so we ignore it.
            if (
                game_state.get_screen_without_blinking_cursor()
                == new_game_state.get_screen_without_blinking_cursor()
            ):
                successes += 1
            else:
                successes = 0
            game_state = new_game_state
            await asyncio.sleep(0.1)

    async def save_game_state(self, path: Path) -> None:
        """Save the current game state to a file."""
        self._check_stopped()
        await asyncio.to_thread(self._save_state_sync, path)

    def _save_state_sync(self, path: Path) -> None:
        """Synchronous helper method to save game state."""
        with path.open("wb") as f:
            self._pyboy.save_state(f)

    def _check_stopped(self) -> None:
        if self._is_stopped:
            raise EmulatorIsStoppedError()

    def _tick(self, count: int = 1) -> bool:
        """
        Tick the emulator forward by `count` frames.

        :param count: Number of frames to tick forward.
        :return: Whether the game is still running.
        """
        self._check_stopped()
        self.tick_num += count
        return self._pyboy.tick(count, render=True, sound=True)
