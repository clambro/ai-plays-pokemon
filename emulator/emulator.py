"""PyBoy integration for controlling Pokémon Yellow."""

import asyncio
import base64
import io
from contextlib import AbstractAsyncContextManager
from copy import deepcopy
from typing import TYPE_CHECKING, Self

from PIL import Image

from common.constants import DEFAULT_ROM_PATH
from emulator.control_events import ControlBoundary
from emulator.game_state import GameState
from emulator.parsers.map_collision import read_map_collision_tiles
from emulator.pyboy_worker import PyBoyWorker
from emulator.text_events import TextEventKind, TextEventReducer, drive_standard_dialog

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from pyboy import PyBoy

    from common.enums import Button
    from emulator.control_events import ControlResult
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
        self._text_event_reducer = TextEventReducer()

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

    async def get_game_state_with_control_boundary(
        self,
    ) -> tuple[GameState, ControlBoundary | None]:
        """Capture parsed game state and its rendered ROM decision boundary."""
        return await self._worker.execute_with_control_boundary(
            lambda pyboy: GameState.from_memory(pyboy.memory)
        )

    def drain_text_events(self) -> tuple[TextEvent, ...]:
        """Claim every currently recorded text event exactly once."""
        return self._worker.drain_text_events()

    async def wait_for_text_events(
        self,
        max_wait_seconds: float | None = None,
    ) -> tuple[TextEvent, ...]:
        """Wait without blocking emulation, then claim the available event batch."""
        return await self._worker.wait_for_text_events(max_wait_seconds)

    async def advance_battle_dialog(self) -> str:
        """Advance battle dialog until the next decision or battle exit."""
        initial_snapshot = await self._worker.drain_settled_text_events_with_control_boundary()
        return await drive_standard_dialog(
            self,
            reducer=self._text_event_reducer,
            stop_on=frozenset(
                {
                    TextEventKind.MENU_OPENED,
                    TextEventKind.SPECIAL_INTERFACE_OPENED,
                    TextEventKind.BATTLE_ENDED,
                }
            ),
            initial_snapshot=initial_snapshot,
        )

    async def advance_text_dialog(
        self,
        *,
        before_input: Callable[[], Awaitable[None]] | None = None,
    ) -> str:
        """Advance ordinary dialog until the interaction changes domain or closes."""
        initial_snapshot = await self._worker.drain_settled_text_events_with_control_boundary()
        return await drive_standard_dialog(
            self,
            reducer=self._text_event_reducer,
            stop_on=frozenset(
                {
                    TextEventKind.MENU_OPENED,
                    TextEventKind.SPECIAL_INTERFACE_OPENED,
                    TextEventKind.INTERACTION_CLOSED,
                    TextEventKind.OVERWORLD_ENTERED,
                    TextEventKind.BATTLE_ENDED,
                }
            ),
            initial_snapshot=initial_snapshot,
            before_input=before_input,
        )

    def consume_pending_dialog(self) -> str:
        """Claim and reduce dialog already completed by the ROM."""
        return self._text_event_reducer.reduce(self.drain_text_events())

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

    async def get_game_state_with_screenshot_and_control_boundary(
        self,
    ) -> tuple[GameState, Image.Image, ControlBoundary | None]:
        """Capture game state, screenshot, and rendered ROM boundary together."""

        def _capture(pyboy: PyBoy) -> tuple[GameState, Image.Image]:
            game_state = GameState.from_memory(pyboy.memory)
            screenshot = deepcopy(pyboy.screen.image)
            if not isinstance(screenshot, Image.Image):
                raise TypeError("No screenshot available")
            return game_state, screenshot

        (game_state, screenshot), boundary = await self._worker.execute_with_control_boundary(
            _capture
        )
        return game_state, screenshot, boundary

    async def press_button(
        self,
        button: Button,
    ) -> ControlResult:
        """Send a button and wait for the active input domain's rendered boundary.

        Args:
            button: Game Boy button to press.

        Returns:
            The resulting control boundary.

        Raises:
            RuntimeError: The emulator has been stopped.
        """
        operation_id = await self._worker.start_control_button(button)
        return await self._worker.wait_for_control_result(operation_id)

    async def pulse_button(self, button: Button) -> None:
        """Send a short button pulse whose completion is owned by a dialog driver."""
        await self._worker.pulse_button(button)

    async def press_overworld_button(
        self,
        button: Button,
        *,
        observe_steps: bool = False,
    ) -> ControlResult:
        """Press an overworld button and wait for its next rendered decision boundary."""
        operation_id = await self._worker.start_overworld_button(
            button,
            observe_steps=observe_steps,
        )
        return await self._worker.wait_for_control_result(operation_id)

    async def advance_text_dialog_until_overworld_ready(self) -> str:
        """Advance an active interaction through restored external overworld control."""
        dialog = await self.advance_text_dialog()
        await self.wait_for_overworld_ready()
        return dialog

    async def wait_for_overworld_ready(self) -> ControlResult:
        """Wait for scripted activity to restore external overworld control."""
        operation_id = await self._worker.start_boundary_wait(ControlBoundary.OVERWORLD_READY)
        return await self._worker.wait_for_control_result(operation_id)

    async def wait_for_menu_ready(self) -> ControlResult:
        """Wait until a standard menu has completed cursor placement and rendering."""
        operation_id = await self._worker.start_boundary_wait(ControlBoundary.MENU_READY)
        return await self._worker.wait_for_control_result(operation_id)

    async def wait_until_ready(self) -> ControlResult:
        """Wait until the ROM reaches any rendered external decision boundary."""
        operation_id = await self._worker.start_boundary_wait()
        return await self._worker.wait_for_control_result(operation_id)

    async def get_emulator_save_state(self) -> str:
        """Get the current save state as a Base64 encoded string."""

        def _capture_save_state(pyboy: PyBoy) -> str:
            with io.BytesIO() as file:
                pyboy.save_state(file)
                return base64.b64encode(file.getvalue()).decode("utf-8")

        return await self._worker.execute(_capture_save_state)
