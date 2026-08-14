"""Transient completion results from ROM control boundaries."""

import asyncio
from dataclasses import dataclass
from enum import StrEnum, auto
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from emulator.game_state import GameState


class ControlBoundary(StrEnum):
    """Decision-ready ROM boundaries used to complete a button operation."""

    OVERWORLD_READY = auto()
    MENU_READY = auto()
    NAMING_READY = auto()
    RENDER_READY = auto()
    SPECIAL_INTERFACE_READY = auto()
    TEXT_INPUT_READY = auto()


@dataclass(frozen=True, slots=True, kw_only=True)
class ControlResult:
    """The rendered boundary reached by one control operation."""

    boundary: ControlBoundary
    step_observations: tuple[GameState, ...] = ()


class ControlResultWaiter:
    """Hand completed control operations from the owner thread to async callers."""

    def __init__(self) -> None:
        """Create an unbound waiter with no completed operations."""
        self._lock = Lock()
        self._results: dict[int, ControlResult] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._notification: asyncio.Event | None = None
        self._closed = False

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind asynchronous notifications before the owner thread starts."""
        with self._lock:
            if self._loop is not None:
                raise RuntimeError("Control result waiter is already bound.")
            self._loop = loop
            self._notification = asyncio.Event()

    def publish(self, operation_id: int, result: ControlResult) -> None:
        """Publish a result after the tick containing its boundary has rendered."""
        with self._lock:
            if self._closed:
                return
            self._results[operation_id] = result
            loop = self._loop
            notification = self._notification

        if loop is not None and notification is not None:
            loop.call_soon_threadsafe(notification.set)

    async def wait(self, operation_id: int) -> ControlResult:
        """Wait for one operation without blocking emulator execution."""
        notification = self._notification
        if notification is None:
            raise RuntimeError("Control result waiter is not bound.")

        while True:
            with self._lock:
                if result := self._results.pop(operation_id, None):
                    return result
                if self._closed:
                    raise RuntimeError("Emulator stopped before reaching a control boundary.")
                notification.clear()
            await notification.wait()

    def close(self) -> None:
        """Wake pending consumers when the emulator owner thread terminates."""
        with self._lock:
            self._closed = True
            loop = self._loop
            notification = self._notification
        if loop is not None and notification is not None:
            loop.call_soon_threadsafe(notification.set)
