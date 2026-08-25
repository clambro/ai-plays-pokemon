"""Transient ROM text events and transcript reduction."""

import asyncio
from dataclasses import dataclass
from enum import StrEnum, auto
from threading import Lock
from typing import TYPE_CHECKING

from common.enums import Button, MapEntityType, MapId
from emulator.control_events import ControlBoundary

if TYPE_CHECKING:
    from emulator.emulator import Emulator


class TextEventKind(StrEnum):
    """Semantic execution boundaries emitted by the supported ROM."""

    MAP_ENTITY_INTERACTION_STARTED = auto()
    MAP_ENTITY_INTERACTION_ENDED = auto()
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
class MapEntityInteractionTarget:
    """Map-qualified entity that originated one text interaction."""

    map_id: MapId
    entity_type: MapEntityType
    entity_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletedMapEntityInteraction:
    """Literal dialog observed during one completed map-entity interaction."""

    target: MapEntityInteractionTarget
    text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TextEvent:
    """One ordered semantic event copied from emulator execution."""

    sequence: int
    frame: int
    kind: TextEventKind
    page: DialogPage | None = None
    interaction_target: MapEntityInteractionTarget | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class TextEventSnapshot:
    """Unread text events and the rendered control boundary observed with them."""

    events: tuple[TextEvent, ...] = ()
    boundary: ControlBoundary | None = None


class TextEventReducer:
    """Reduce ordered text events while retaining the active dialog page."""

    def __init__(self) -> None:
        """Start without a preceding dialog page."""
        self._previous_page: DialogPage | None = None
        self._active_interaction_target: MapEntityInteractionTarget | None = None
        self._active_interaction_lines: list[str] = []
        self._completed_map_entity_interactions: list[CompletedMapEntityInteraction] = []

    def reduce(self, events: tuple[TextEvent, ...] | list[TextEvent]) -> str:
        """Combine stable dialog pages without repeated snapshots or scrolled lines."""
        transcript: list[str] = []
        for event in events:
            if self._apply_map_entity_boundary(event):
                continue

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
                    self._previous_page = None
                if event.kind in {
                    TextEventKind.INTERACTION_CLOSED,
                    TextEventKind.OVERWORLD_ENTERED,
                    TextEventKind.BATTLE_ENDED,
                }:
                    self._complete_map_entity_interaction()
                continue
            if page == self._previous_page:
                continue

            new_lines = []
            top_line_scrolled = (
                self._previous_page is not None and page.top_line == self._previous_page.bottom_line
            )
            if page.top_line and not top_line_scrolled:
                new_lines.append(page.top_line)
            if page.bottom_line:
                new_lines.append(page.bottom_line)
            transcript.extend(new_lines)
            if self._active_interaction_target is not None:
                self._active_interaction_lines.extend(new_lines)
            self._previous_page = page
        return " ".join(transcript).strip()

    def _apply_map_entity_boundary(self, event: TextEvent) -> bool:
        """Apply an entity interaction start or end event when present."""
        if event.kind == TextEventKind.MAP_ENTITY_INTERACTION_STARTED:
            self._complete_map_entity_interaction()
            self._active_interaction_target = event.interaction_target
        elif event.kind == TextEventKind.MAP_ENTITY_INTERACTION_ENDED:
            self._complete_map_entity_interaction()
        else:
            return False
        self._previous_page = None
        return True

    def drain_completed_map_entity_interactions(
        self,
    ) -> tuple[CompletedMapEntityInteraction, ...]:
        """Claim completed map-entity interactions exactly once."""
        interactions = tuple(self._completed_map_entity_interactions)
        self._completed_map_entity_interactions.clear()
        return interactions

    def _complete_map_entity_interaction(self) -> None:
        """Finish the active entity observation at a semantic interaction boundary."""
        if self._active_interaction_target is not None and self._active_interaction_lines:
            self._completed_map_entity_interactions.append(
                CompletedMapEntityInteraction(
                    target=self._active_interaction_target,
                    text=" ".join(self._active_interaction_lines).strip(),
                )
            )
        self._active_interaction_target = None
        self._active_interaction_lines.clear()


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
        interaction_target: MapEntityInteractionTarget | None = None,
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
                interaction_target=interaction_target,
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


async def drive_standard_dialog(
    emulator: Emulator,
    *,
    reducer: TextEventReducer,
    stop_on: frozenset[TextEventKind],
    initial_snapshot: TextEventSnapshot | None = None,
) -> str:
    """Advance explicit dialog waits until the requested ROM boundary."""
    initial_snapshot = initial_snapshot or TextEventSnapshot()
    events: list[TextEvent] = []
    batch = initial_snapshot.events
    initial_batch = bool(batch)
    control = _DialogControlState(
        input_required=(
            not batch and initial_snapshot.boundary == ControlBoundary.TEXT_INPUT_READY
        ),
        waiting_for_initial_menu_exit=initial_batch,
    )

    while True:
        if batch:
            events.extend(batch)

            reached_boundary = control.apply(
                batch,
                initial_batch=initial_batch,
                stop_on=stop_on,
            )
            initial_batch = False

            if reached_boundary:
                if control.menu_open and TextEventKind.MENU_OPENED in stop_on:
                    await emulator.wait_for_menu_ready()
                else:
                    await emulator.wait_until_ready()
                events.extend(emulator.drain_text_events())
                return reducer.reduce(events)

            if any(event.kind == TextEventKind.INPUT_RESOLVED for event in batch):
                boundary = (await emulator.wait_until_ready()).boundary
                if boundary != ControlBoundary.TEXT_INPUT_READY:
                    events.extend(emulator.drain_text_events())
                    return reducer.reduce(events)

        if control.input_required and not control.input_sent:
            await emulator.press_button(Button.A)
            control.input_sent = True

        batch = await emulator.wait_for_text_events()
        if not batch:
            raise RuntimeError("Emulator stopped before dialog reached a semantic boundary.")
