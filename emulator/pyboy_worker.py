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

if TYPE_CHECKING:
    from pathlib import Path

_HEADLESS_TICK_SLEEP_SECONDS = 0.002

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

    async def start(self) -> None:
        """Start the owner thread and wait for PyBoy initialization."""
        with self._state_lock:
            if self._started:
                raise RuntimeError("Emulator has already been started.")
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
                if self._headless:
                    time.sleep(_HEADLESS_TICK_SLEEP_SECONDS)
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
