"""Transient ROM text events and transcript reduction."""

import asyncio
from dataclasses import dataclass
from enum import StrEnum, auto
from threading import Lock


class TextEventKind(StrEnum):
    """Semantic boundaries emitted by the supported ROM's text engine."""

    PAGE_COMPLETED = auto()
    AUTOMATIC_SCROLL = auto()
    INPUT_REQUIRED = auto()
    INPUT_RESOLVED = auto()
    MENU_OPENED = auto()
    INTERACTION_CLOSED = auto()
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
                TextEventKind.INTERACTION_CLOSED,
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
