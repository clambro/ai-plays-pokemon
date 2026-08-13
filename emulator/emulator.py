"""PyBoy integration for controlling Pokémon Yellow."""

import asyncio
import base64
import io
from contextlib import AbstractAsyncContextManager
from copy import deepcopy
from typing import TYPE_CHECKING, Self

from PIL import Image

from common.constants import DEFAULT_ROM_PATH
from emulator.game_state import GameState
from emulator.parsers.map_collision import read_map_collision_tiles
from emulator.pyboy_worker import PyBoyWorker

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pyboy import PyBoy

    from common.enums import Button
    from emulator.text_events import TextEvent


class Emulator(AbstractAsyncContextManager):
    """Control Pokémon Yellow Legacy through a thread-owned PyBoy instance.

    The public API owns Pokémon-specific behavior. A private worker owns PyBoy and executes each
    requested operation on its dedicated thread.

    Args:
        rom_path: Path to the ROM to load.
        save_state: Base64-encoded state to restore.
        save_state_path: File containing a state to restore.
        mute_sound: Whether to initialize PyBoy with zero volume.
        headless: Whether to use PyBoy's null window instead of SDL.

    Raises:
        ValueError: Both ``save_state`` and ``save_state_path`` are provided.
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

        self._worker = PyBoyWorker(
            rom_path,
            save_state,
            save_state_path,
            mute_sound=mute_sound,
            headless=headless,
        )

    async def __aenter__(self) -> Self:
        """Start the PyBoy worker when entering the context."""
        await self._worker.start()
        try:
            await asyncio.sleep(1)  # Give the emulator time to load before continuing.
        except asyncio.CancelledError:
            await self._worker.stop()
            raise
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Stop the PyBoy worker when exiting the context."""
        shutdown_error: Exception | None = None
        try:
            await self._worker.stop()
        except Exception as exc:  # noqa: BLE001
            # Preserve worker failures without masking an exception from the context body.
            shutdown_error = exc

        if exc_type is None and shutdown_error is not None:
            raise shutdown_error

    async def get_game_state(self) -> GameState:
        """Get the current game state."""
        return await self._worker.execute(lambda pyboy: GameState.from_memory(pyboy.memory))

    def drain_text_events(self) -> tuple[TextEvent, ...]:
        """Claim every currently recorded text event exactly once."""
        return self._worker.drain_text_events()

    async def wait_for_text_events(
        self,
        max_wait_seconds: float | None = None,
    ) -> tuple[TextEvent, ...]:
        """Wait without blocking emulation, then claim the available event batch."""
        return await self._worker.wait_for_text_events(max_wait_seconds)

    async def get_game_state_with_map_collision_tiles(
        self,
    ) -> tuple[GameState, list[list[int]]]:
        """Get the current game state and its full map collision grid on demand."""

        def _capture(pyboy: PyBoy) -> tuple[GameState, list[list[int]]]:
            return GameState.from_memory(pyboy.memory), read_map_collision_tiles(pyboy.memory)

        return await self._worker.execute(_capture)

    async def get_game_state_with_screenshot(
        self,
    ) -> tuple[GameState, Image.Image]:
        """Capture the current game state and screen image together.

        Returns:
            The current game state and a copied screen image captured without allowing the emulator
            to tick between them.

        Raises:
            RuntimeError: The emulator has been stopped.
            TypeError: PyBoy exposes no valid screenshot.
        """

        def _capture_game_state_with_screenshot(
            pyboy: PyBoy,
        ) -> tuple[GameState, Image.Image]:
            game_state = GameState.from_memory(pyboy.memory)
            screenshot = deepcopy(pyboy.screen.image)
            if not isinstance(screenshot, Image.Image):
                raise TypeError("No screenshot available")
            return game_state, screenshot

        return await self._worker.execute(_capture_game_state_with_screenshot)

    async def press_button(
        self,
        button: Button,
        *,
        wait_for_animation: bool = True,
    ) -> None:
        """Send a button press and optionally wait for animations to finish.

        Args:
            button: Game Boy button to press.
            wait_for_animation: Whether to wait for the resulting screen animation. Disable this
                only when the caller handles subsequent activity itself.

        Raises:
            RuntimeError: The emulator has been stopped.
        """
        # If we're deferring animation handling, we want to exit as quickly as possible. Two frames
        # seems to be the minimum to guarantee that the button press is registered.
        hold_frames = 10 if wait_for_animation else 2
        await self._worker.execute(lambda pyboy: pyboy.button(button, hold_frames))
        if wait_for_animation:
            await self.wait_for_animation_to_finish()

    async def wait_for_animation_to_finish(
        self,
        on_game_state: Callable[[GameState], None] | None = None,
    ) -> GameState:
        """Wait until all ongoing animations have finished.

        The various hyperparameters here are a bit wishy-washy. I determined emperically that they
        work pretty well, but they're probably not optimal, especially since different scenarios
        have different animation speeds.

        Args:
            on_game_state: Optional observer called for each state already read while waiting.

        Returns:
            The final observed game state.
        """
        successes = 0
        required_successes = 5
        game_state = await self.get_game_state()
        if on_game_state:
            on_game_state(game_state)
        while successes < required_successes:
            await asyncio.sleep(0.15)
            new_game_state = await self.get_game_state()
            if on_game_state:
                on_game_state(new_game_state)
            if (
                # The blinking cursor should not block progress, so we ignore it.
                game_state.screen.tiles_without_cursor == new_game_state.screen.tiles_without_cursor
                and game_state.map.id == new_game_state.map.id
                and game_state.player.coords == new_game_state.player.coords
                and game_state.player.direction == new_game_state.player.direction
            ):
                successes += 1
            else:
                successes = 0
            game_state = new_game_state
        return game_state

    async def get_emulator_save_state(self) -> str:
        """Get the current save state as a Base64 encoded string."""

        def _capture_save_state(pyboy: PyBoy) -> str:
            with io.BytesIO() as file:
                pyboy.save_state(file)
                return base64.b64encode(file.getvalue()).decode("utf-8")

        return await self._worker.execute(_capture_save_state)
