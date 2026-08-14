"""Transient ROM text events and transcript reduction."""

import asyncio
from dataclasses import dataclass
from enum import StrEnum, auto
from threading import Lock
from typing import TYPE_CHECKING

from common.enums import Button

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from emulator.emulator import Emulator


class TextEventKind(StrEnum):
    """Semantic execution boundaries emitted by the supported ROM."""

    PAGE_COMPLETED = auto()
    AUTOMATIC_SCROLL = auto()
    INPUT_REQUIRED = auto()
    INPUT_RESOLVED = auto()
    MENU_OPENED = auto()
    MENU_CLOSED = auto()
    SPECIAL_INTERFACE_OPENED = auto()
    SPECIAL_INTERFACE_CLOSED = auto()
    INTERACTION_CLOSED = auto()
    OVERWORLD_ENTERED = auto()
    BATTLE_ENDED = auto()


@dataclass(frozen=True, slots=True, kw_only=True)
class DialogPage:
    """Stable contents of the standard two-row dialog box."""

    top_line: str
    bottom_line: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TextEvent:
    """One ordered semantic event copied from emulator execution."""

    sequence: int
    frame: int
    kind: TextEventKind
    page: DialogPage | None = None


@dataclass(slots=True)
class _DialogControlState:
    """Current standard-dialog and menu state reduced from ordered events."""

    input_required: bool = False
    input_sent: bool = False
    menu_open: bool = False
    waiting_for_initial_menu_exit: bool = False

    def apply(
        self,
        events: tuple[TextEvent, ...],
        *,
        initial_batch: bool,
        stop_on: frozenset[TextEventKind],
    ) -> bool:
        """Apply one event batch and report whether a requested boundary is active."""
        reached_boundary = False
        for event in events:
            if event.kind == TextEventKind.INPUT_REQUIRED:
                self.input_required = True
                self.input_sent = False
            elif event.kind == TextEventKind.INPUT_RESOLVED:
                self.input_required = False
                self.input_sent = False
            elif event.kind == TextEventKind.MENU_OPENED:
                self.menu_open = True
            elif event.kind == TextEventKind.MENU_CLOSED:
                self.menu_open = False
                self.waiting_for_initial_menu_exit = False

            reached_boundary |= event.kind in stop_on - {TextEventKind.MENU_OPENED}

        if initial_batch and self.waiting_for_initial_menu_exit:
            self.waiting_for_initial_menu_exit = self.menu_open
        menu_boundary = (
            self.menu_open
            and not self.waiting_for_initial_menu_exit
            and TextEventKind.MENU_OPENED in stop_on
        )
        return reached_boundary or menu_boundary


class TextEventJournal:
    """Thread-safe, exactly-once handoff from PyBoy callbacks to async consumers."""

    def __init__(self) -> None:
        """Create an unbound empty journal."""
        self._lock = Lock()
        self._events: list[TextEvent] = []
        self._next_sequence = 1
        self._loop: asyncio.AbstractEventLoop | None = None
        self._notification: asyncio.Event | None = None
        self._closed = False

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind asynchronous notifications before the owner thread starts."""
        with self._lock:
            if self._loop is not None:
                raise RuntimeError("Text event journal is already bound.")
            self._loop = loop
            self._notification = asyncio.Event()

    def append(
        self,
        *,
        frame: int,
        kind: TextEventKind,
        page: DialogPage | None = None,
    ) -> TextEvent | None:
        """Append an event from the PyBoy owner thread and wake async consumers."""
        with self._lock:
            if self._closed:
                return None
            event = TextEvent(
                sequence=self._next_sequence,
                frame=frame,
                kind=kind,
                page=page,
            )
            self._next_sequence += 1
            self._events.append(event)
            loop = self._loop
            notification = self._notification

        if loop is not None and notification is not None:
            loop.call_soon_threadsafe(notification.set)
        return event

    def drain(self) -> tuple[TextEvent, ...]:
        """Claim every currently available event exactly once."""
        with self._lock:
            events = tuple(self._events)
            self._events.clear()
        return events

    def drain_through_last(self, kind: TextEventKind) -> tuple[TextEvent, ...]:
        """Claim events through the last available boundary of the requested kind."""
        with self._lock:
            boundary = next(
                (
                    index
                    for index in range(len(self._events) - 1, -1, -1)
                    if self._events[index].kind == kind
                ),
                None,
            )
            if boundary is None:
                return ()
            events = tuple(self._events[: boundary + 1])
            del self._events[: boundary + 1]
        return events

    async def wait_and_drain(
        self,
        max_wait_seconds: float | None = None,
    ) -> tuple[TextEvent, ...]:
        """Wait asynchronously for an event batch, then claim the complete batch."""
        notification = self._notification
        if notification is None:
            raise RuntimeError("Text event journal is not bound.")

        events = self.drain()
        if events:
            return events

        notification.clear()
        # An append may have raced with clearing the notification. Recheck while preserving the
        # event itself rather than relying on notification state as the source of truth.
        events = self.drain()
        if events:
            return events

        with self._lock:
            if self._closed:
                return ()

        try:
            await asyncio.wait_for(notification.wait(), timeout=max_wait_seconds)
        except TimeoutError:
            return ()
        return self.drain()

    def close(self) -> None:
        """Wake pending consumers when the emulator owner thread terminates."""
        with self._lock:
            self._closed = True
            loop = self._loop
            notification = self._notification
        if loop is not None and notification is not None:
            loop.call_soon_threadsafe(notification.set)


def reduce_text_events(events: tuple[TextEvent, ...] | list[TextEvent]) -> str:
    """Combine stable dialog pages without repeated snapshots or scrolled lines."""
    transcript: list[str] = []
    previous_page: DialogPage | None = None
    for event in events:
        page = event.page
        if page is None:
            if event.kind in {
                TextEventKind.MENU_OPENED,
                TextEventKind.MENU_CLOSED,
                TextEventKind.SPECIAL_INTERFACE_OPENED,
                TextEventKind.SPECIAL_INTERFACE_CLOSED,
                TextEventKind.INTERACTION_CLOSED,
                TextEventKind.OVERWORLD_ENTERED,
                TextEventKind.BATTLE_ENDED,
            }:
                previous_page = None
            continue
        if page == previous_page:
            continue

        top_line_scrolled = previous_page is not None and page.top_line == previous_page.bottom_line
        if page.top_line and not top_line_scrolled:
            transcript.append(page.top_line)
        if page.bottom_line:
            transcript.append(page.bottom_line)
        previous_page = page
    return " ".join(transcript).strip()


async def drive_standard_dialog(
    emulator: Emulator,
    *,
    stop_on: frozenset[TextEventKind],
    initial_events: tuple[TextEvent, ...] = (),
    before_input: Callable[[], Awaitable[None]] | None = None,
) -> str:
    """Advance explicit dialog waits until the requested ROM boundary."""
    events: list[TextEvent] = []
    batch = initial_events
    initial_batch = bool(batch)
    control = _DialogControlState(waiting_for_initial_menu_exit=initial_batch)

    while True:
        if not batch:
            batch = await emulator.wait_for_text_events()
        if not batch:
            raise RuntimeError("Emulator stopped before dialog reached a semantic boundary.")
        events.extend(batch)

        reached_boundary = control.apply(
            batch,
            initial_batch=initial_batch,
            stop_on=stop_on,
        )
        initial_batch = False

        if reached_boundary:
            return reduce_text_events(events)

        if control.input_required and not control.input_sent:
            if before_input is not None:
                await before_input()
            await emulator.press_button(Button.A, wait_for_animation=False)
            control.input_sent = True
        batch = ()
