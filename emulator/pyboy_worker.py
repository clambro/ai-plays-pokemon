"""Thread ownership and command execution for PyBoy."""

import asyncio
import base64
import io
import time
from collections.abc import Callable
from concurrent.futures import Future
from queue import Empty, Queue
from threading import Lock, Thread
from typing import TYPE_CHECKING

from pyboy import PyBoy

from emulator.control_events import ControlBoundary, ControlResultWaiter
from emulator.game_state import GameState
from emulator.rom_hooks.control import RomControlHooks
from emulator.rom_hooks.text import RomTextHooks
from emulator.text_events import (
    TextEvent,
    TextEventJournal,
    TextEventKind,
    TextEventSnapshot,
)

if TYPE_CHECKING:
    from pathlib import Path

    from common.enums import Button
    from emulator.control_events import ControlResult


type _QueuedCommand = tuple[Callable[[PyBoy], None], Callable[[Exception], None]]


class PyBoyWorker:
    """Own PyBoy and execute submitted operations on its dedicated thread."""

    def __init__(
        self,
        rom_path: str,
        save_state: str | None,
        save_state_path: Path | None,
        *,
        mute_sound: bool,
        headless: bool,
    ) -> None:
        """Initialize the worker without constructing PyBoy."""
        self._rom_path = rom_path
        self._save_state = save_state
        self._save_state_path = save_state_path
        self._mute_sound = mute_sound
        self._headless = headless

        self._commands: Queue[_QueuedCommand | None] = Queue()
        self._state_lock = Lock()
        self._accepting_commands = False
        self._started = False
        self._failure: Exception | None = None
        self._startup: Future[None] = Future()
        self._termination: Future[None] = Future()
        self._thread = Thread(target=self._run, name="pyboy-owner")
        self._control_results = ControlResultWaiter()
        self._control_hooks: RomControlHooks | None = None
        self._text_events = TextEventJournal()
        self._text_hooks: RomTextHooks | None = None

    async def start(self) -> None:
        """Start the owner thread and wait for PyBoy initialization."""
        with self._state_lock:
            if self._started:
                raise RuntimeError("Emulator has already been started.")
            self._control_results.bind(asyncio.get_running_loop())
            self._text_events.bind(asyncio.get_running_loop())
            self._started = True
            self._accepting_commands = True

        try:
            self._thread.start()
        except Exception as exc:  # noqa: BLE001
            # Surface thread startup failure through the same path as PyBoy startup failure.
            self._finish(exc)

        startup_waiter = asyncio.wrap_future(self._startup)
        try:
            await asyncio.shield(startup_waiter)
        except asyncio.CancelledError:
            self._request_stop()
            await self._wait_for_termination()
            # The shielded startup waiter may hold a construction error that cleanup superseded.
            startup_waiter.exception()
            raise
        except Exception:
            cancellation = await self._wait_for_termination()
            if cancellation is not None:
                raise cancellation from None
            raise

    async def execute[ResultT](self, operation: Callable[[PyBoy], ResultT]) -> ResultT:
        """Execute an operation on the owner thread and return its result."""
        future: Future[ResultT] = Future()

        def execute(pyboy: PyBoy) -> None:
            try:
                result = operation(pyboy)
            except Exception as exc:  # noqa: BLE001
                # Arbitrary submitted operations report their own failures without killing PyBoy.
                if not future.done():
                    future.set_exception(exc)
            else:
                if not future.done():
                    future.set_result(result)

        def fail(exc: Exception) -> None:
            if not future.done():
                future.set_exception(exc)

        with self._state_lock:
            if self._accepting_commands:
                self._commands.put((execute, fail))
            else:
                fail(self._failure or RuntimeError("Emulator is stopped."))

        return await asyncio.wrap_future(future)

    async def execute_with_control_boundary[ResultT](
        self,
        operation: Callable[[PyBoy], ResultT],
    ) -> tuple[ResultT, ControlBoundary | None]:
        """Execute an operation and capture the active ROM boundary atomically."""

        def _capture(pyboy: PyBoy) -> tuple[ResultT, ControlBoundary | None]:
            if self._control_hooks is None:
                raise RuntimeError("ROM control hooks are not installed.")
            return operation(pyboy), self._control_hooks.current_boundary

        return await self.execute(_capture)

    async def stop(self) -> None:
        """Stop PyBoy on its owner thread and wait for thread termination."""
        with self._state_lock:
            if not self._started:
                raise RuntimeError("Emulator has not been started.")
            if self._accepting_commands:
                self._accepting_commands = False
                self._commands.put(None)

        cancellation = await self._wait_for_termination()
        if cancellation is not None:
            raise cancellation
        if self._failure is not None:
            raise self._failure

    async def start_overworld_button(
        self,
        button: Button,
        *,
        observe_steps: bool = False,
    ) -> int:
        """Arm overworld coordination and hold its button until the ROM accepts it."""

        def _start(pyboy: PyBoy) -> int:
            if self._control_hooks is None:
                raise RuntimeError("ROM control hooks are not installed.")
            operation_id = self._control_hooks.arm_overworld_button(
                button,
                observe_steps=observe_steps,
            )
            pyboy.button_press(button)
            return operation_id

        return await self.execute(_start)

    async def start_control_button(self, button: Button) -> int:
        """Arm coordination and hold its button until the active input domain accepts it."""

        def _start(pyboy: PyBoy) -> int:
            if self._control_hooks is None:
                raise RuntimeError("ROM control hooks are not installed.")
            operation_id = self._control_hooks.arm_button(button)
            pyboy.button_press(button)
            return operation_id

        return await self.execute(_start)

    async def pulse_button(self, button: Button) -> None:
        """Schedule input whose subsequent completion is owned by a dialog driver."""

        def _pulse(pyboy: PyBoy) -> None:
            if self._control_hooks is None:
                raise RuntimeError("ROM control hooks are not installed.")
            self._control_hooks.begin_raw_input()
            pyboy.button(button, 2)

        await self.execute(_pulse)

    async def start_boundary_wait(self, boundary: ControlBoundary | None = None) -> int:
        """Arm a wait for a requested or arbitrary ready ROM boundary."""

        def _start(_pyboy: PyBoy) -> int:
            if self._control_hooks is None:
                raise RuntimeError("ROM control hooks are not installed.")
            return self._control_hooks.arm_boundary_wait(boundary)

        return await self.execute(_start)

    async def wait_for_control_result(self, operation_id: int) -> ControlResult:
        """Wait for the rendered decision boundary following an accepted input."""
        return await self._control_results.wait(operation_id)

    def drain_text_events(self) -> tuple[TextEvent, ...]:
        """Claim every currently recorded text event exactly once."""
        return self._text_events.drain()

    async def drain_settled_text_events_with_control_boundary(
        self,
    ) -> TextEventSnapshot:
        """Claim pending text events with their current rendered control boundary."""

        def _drain(_pyboy: PyBoy) -> TextEventSnapshot:
            if self._control_hooks is None:
                raise RuntimeError("ROM control hooks are not installed.")
            return TextEventSnapshot(
                events=self._text_events.drain(),
                boundary=self._control_hooks.current_boundary,
            )

        return await self.execute(_drain)

    def drain_completed_text_events(self) -> tuple[TextEvent, ...]:
        """Claim text events whose ordinary interaction has already closed."""
        return self._text_events.drain_through_last(TextEventKind.INTERACTION_CLOSED)

    async def wait_for_text_events(
        self,
        max_wait_seconds: float | None = None,
    ) -> tuple[TextEvent, ...]:
        """Wait without blocking PyBoy, then claim the complete available event batch."""
        events = await self._text_events.wait_and_drain(max_wait_seconds)
        if not events:
            return ()

        # A hook wakes the async consumer from inside tick(). Drain again at the next owner-thread
        # command boundary so every event from that emulated frame is considered before input.
        settled_events = await self.execute(lambda _pyboy: self._text_events.drain())
        return events + settled_events

    def _run(self) -> None:
        pyboy: PyBoy | None = None
        pyboy_stopped = False
        failure: Exception | None = None
        try:
            pyboy = self._create_pyboy()
            if not self._startup.done():
                self._startup.set_result(None)

            while True:
                if self._process_commands(pyboy):
                    pyboy_stopped = True
                    break
                if not pyboy.tick(1, render=True, sound=True):
                    failure = RuntimeError("Emulator stopped unexpectedly.")
                    break
                if self._control_hooks is not None:
                    step_observation = (
                        GameState.from_memory(pyboy.memory)
                        if self._control_hooks.needs_step_observation
                        else None
                    )
                    self._control_hooks.publish_tick(step_observation)
                # PyBoy's SDL limiter skips its own sleep while refilling a low audio buffer.
                # Without this minimum delay, the tight worker loop runs catch-up frames
                # back-to-back, causing brief audio and visual speed-ups after scheduling jitter.
                # PyBoy adjusts its normal SDL sleep around this delay, preserving real-time speed.
                time.sleep(0.002)
        except Exception as exc:  # noqa: BLE001
            # Every worker failure must reach pending and future callers.
            failure = exc
        finally:
            if pyboy is not None and not pyboy_stopped:
                try:
                    pyboy.stop()
                except Exception as exc:  # noqa: BLE001
                    # Cleanup failure is the worker failure if nothing failed earlier.
                    if failure is None:
                        failure = exc
            self._finish(failure)

    def _create_pyboy(self) -> PyBoy:
        volume = 0 if self._mute_sound else 100
        window = "null" if self._headless else "SDL2"
        pyboy = PyBoy(self._rom_path, sound_volume=volume, window=window)

        if self._save_state:
            buffer = io.BytesIO(base64.b64decode(self._save_state))
            buffer.seek(0)  # PyBoy requires this.
            pyboy.load_state(buffer)
        elif self._save_state_path:
            with self._save_state_path.open("rb") as file:
                pyboy.load_state(file)
        self._control_hooks = RomControlHooks(pyboy, self._control_results)
        self._control_hooks.install()
        self._text_hooks = RomTextHooks(
            pyboy,
            self._text_events,
            on_event=self._control_hooks.observe_text_event,
        )
        self._text_hooks.install()
        return pyboy

    def _process_commands(self, pyboy: PyBoy) -> bool:
        while True:
            try:
                command = self._commands.get_nowait()
            except Empty:
                return False

            if command is None:
                pyboy.stop()
                return True

            execute, _ = command
            execute(pyboy)

    def _finish(self, failure: Exception | None) -> None:
        self._control_results.close()
        self._text_events.close()
        pending_failures: list[Callable[[Exception], None]] = []
        terminal_error = failure or RuntimeError("Emulator is stopped.")
        with self._state_lock:
            self._accepting_commands = False
            self._failure = failure
            while True:
                try:
                    command = self._commands.get_nowait()
                except Empty:
                    break
                if command is not None:
                    _, fail = command
                    pending_failures.append(fail)

        for fail in pending_failures:
            fail(terminal_error)
        if not self._startup.done():
            self._startup.set_exception(terminal_error)
        if not self._termination.done():
            self._termination.set_result(None)

    def _request_stop(self) -> None:
        with self._state_lock:
            if self._accepting_commands:
                self._accepting_commands = False
                self._commands.put(None)

    async def _wait_for_termination(self) -> asyncio.CancelledError | None:
        waiter = asyncio.wrap_future(self._termination)
        cancellation: asyncio.CancelledError | None = None
        while not waiter.done():
            try:
                await asyncio.shield(waiter)
            except asyncio.CancelledError as exc:
                cancellation = cancellation or exc
        self._join()
        return cancellation

    def _join(self) -> None:
        if self._thread.ident is not None:
            self._thread.join()
