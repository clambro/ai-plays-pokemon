import asyncio
import base64
import io
from contextlib import AbstractAsyncContextManager, suppress
from copy import deepcopy
from pathlib import Path

from loguru import logger
from PIL import Image
from pyboy import PyBoy

from common.constants import DEFAULT_ROM_PATH
from common.enums import Button
from emulator.game_state import YellowLegacyGameState


class YellowLegacyEmulator(AbstractAsyncContextManager):
    """
    Wrapper for accessing the game state of Pokemon Yellow Legacy. Encapsulates the PyBoy API so
    that the rest of the codebase doesn't need to worry about emulation or memory addresses.
    """

    def __init__(
        self,
        rom_path: str = DEFAULT_ROM_PATH,
        save_state: str | None = None,
        save_state_path: Path | None = None,
        *,
        mute_sound: bool = False,
        headless: bool = False,
    ) -> None:
        """Initialize the emulator."""
        if save_state and save_state_path:
            raise ValueError("Cannot specify both save_state and save_state_path.")

        volume = 0 if mute_sound else 100
        window = "null" if headless else "SDL2"
        self._pyboy = PyBoy(rom_path, sound_volume=volume, window=window)

        if save_state:
            self._pyboy.load_state(io.BytesIO(base64.b64decode(save_state)))
        elif save_state_path:
            with save_state_path.open("rb") as f:
                self._pyboy.load_state(f)

        self._is_stopped = True
        self._tick_task: asyncio.Task | None = None
        self._button_lock = asyncio.Lock()

    async def __aenter__(self) -> "YellowLegacyEmulator":
        """Start the emulator's tick task when entering the context."""
        self._is_stopped = False
        self._tick_task = asyncio.create_task(self.async_tick_indefinitely())
        await asyncio.sleep(1)  # Give the emulator time to load before continuing.
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Stop the emulator and cancel the tick task when exiting the context."""
        self.stop()
        if self._tick_task:
            self._tick_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._tick_task

    def get_game_state(self) -> YellowLegacyGameState:
        """Get the current game state."""
        self._check_stopped()
        return YellowLegacyGameState.from_memory(self._pyboy.memory)

    async def async_tick_indefinitely(self) -> None:
        """Tick the emulator indefinitely. Should be run on its own thread."""
        while True:
            self._check_stopped()
            async with self._button_lock:
                if not self._tick():
                    self.stop()
                    break
            await asyncio.sleep(0.001)  # Pass control back to the event loop.

    def stop(self) -> None:
        """Stop the emulator."""
        self._is_stopped = True
        self._pyboy.stop()

    def get_screenshot(self) -> Image.Image:
        """Get a screenshot of the current game screen."""
        self._check_stopped()
        img = deepcopy(self._pyboy.screen.image)
        if not isinstance(img, Image.Image):
            raise TypeError("No screenshot available")
        return img

    async def press_button(
        self,
        button: Button,
        *,
        wait_for_animation: bool = True,
    ) -> None:
        """
        Send a button press to the emulator and wait for any animations to finish.

        :param button: The button to press.
        :param hold_frames: The number of frames to hold each button.
        :param wait_for_animation: Whether to wait for animations to finish. You usually want this,
            but you can skip it if you have bespoke handling for subsequent activity.
        """
        self._check_stopped()
        # If we're deferring animation handling, we want to exit as quickly as possible. Two frames
        # seems to be the minimum to guarantee that the button press is registered.
        hold_frames = 10 if wait_for_animation else 2
        async with self._button_lock:
            self._pyboy.button(button, hold_frames)
        if wait_for_animation:
            await self.wait_for_animation_to_finish()

    async def wait_for_animation_to_finish(self) -> None:
        """
        Wait until all ongoing animations have finished.

        The various hyperparameters here are a bit wishy-washy. I determined emperically that they
        work pretty well, but they're probably not optimal, especially since different scenarios
        have different animation speeds.
        """
        logger.info("Checking for animations and waiting for them to finish.")
        self._check_stopped()
        successes = 0
        required_successes = 10
        while successes < required_successes:
            game_state = self.get_game_state()
            await asyncio.sleep(0.15)
            new_game_state = self.get_game_state()
            # The blinking cursor should not block progress, so we ignore it.
            if game_state.screen.tiles_without_cursor == new_game_state.screen.tiles_without_cursor:
                successes += 1
            else:
                successes = 0

    async def get_emulator_save_state(self) -> str:
        """Get the current save state as a Base64 encoded string."""
        self._check_stopped()
        with io.BytesIO() as f:
            await asyncio.to_thread(self._pyboy.save_state, f)
            return base64.b64encode(f.getvalue()).decode("utf-8")

    def _check_stopped(self) -> None:
        if self._is_stopped:
            raise RuntimeError("Emulator is stopped.")

    def _tick(self, count: int = 1) -> bool:
        """
        Tick the emulator forward by `count` frames.

        :param count: Number of frames to tick forward.
        :return: Whether the game is still running.
        """
        self._check_stopped()
        return self._pyboy.tick(count, render=True, sound=True)
