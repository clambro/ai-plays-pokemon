"""Unit tests for core text-event logic."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from emulator.text_events import (
    DialogPage,
    TextEvent,
    TextEventJournal,
    TextEventKind,
    drive_standard_dialog,
    reduce_text_events,
)


@pytest.mark.unit
async def test_journal_hands_off_one_ordered_batch() -> None:
    """Wake an async consumer without replaying claimed events."""
    journal = TextEventJournal()
    journal.bind(asyncio.get_running_loop())
    waiter = asyncio.create_task(journal.wait_and_drain(max_wait_seconds=1))
    await asyncio.sleep(0)

    journal.append(frame=8, kind=TextEventKind.PAGE_COMPLETED)
    journal.append(frame=8, kind=TextEventKind.INPUT_REQUIRED)

    events = await waiter
    assert [event.sequence for event in events] == [1, 2]
    assert [event.kind for event in events] == [
        TextEventKind.PAGE_COMPLETED,
        TextEventKind.INPUT_REQUIRED,
    ]
    assert journal.drain() == ()


@pytest.mark.unit
def test_journal_leaves_live_interaction_after_completed_dialog() -> None:
    """Claim closed ephemeral text without taking the next handler's live events."""
    journal = TextEventJournal()
    journal.append(frame=1, kind=TextEventKind.PAGE_COMPLETED)
    journal.append(frame=2, kind=TextEventKind.INTERACTION_CLOSED)
    journal.append(frame=3, kind=TextEventKind.INPUT_REQUIRED)

    completed = journal.drain_through_last(TextEventKind.INTERACTION_CLOSED)

    assert [event.kind for event in completed] == [
        TextEventKind.PAGE_COMPLETED,
        TextEventKind.INTERACTION_CLOSED,
    ]
    assert [event.kind for event in journal.drain()] == [TextEventKind.INPUT_REQUIRED]


@pytest.mark.unit
def test_reduce_text_events_preserves_dialog_without_hook_duplicates() -> None:
    """Deduplicate semantic snapshots and scrolling only within one interaction."""
    first_page = DialogPage(top_line="VOLTAIL used", bottom_line="THUNDERSHOCK!")
    scrolled_page = DialogPage(top_line="THUNDERSHOCK!", bottom_line="It's effective!")
    events = [
        _event(1, TextEventKind.PAGE_COMPLETED, first_page),
        _event(2, TextEventKind.AUTOMATIC_SCROLL, first_page),
        _event(3, TextEventKind.PAGE_COMPLETED, scrolled_page),
        _event(4, TextEventKind.INTERACTION_CLOSED),
        _event(5, TextEventKind.PAGE_COMPLETED, scrolled_page),
    ]

    assert reduce_text_events(events) == (
        "VOLTAIL used THUNDERSHOCK! It's effective! THUNDERSHOCK! It's effective!"
    )


@pytest.mark.unit
async def test_dialog_driver_stops_when_an_initial_menu_is_replaced() -> None:
    """Treat a menu opened after the initial menu closes as a new decision boundary."""
    emulator = MagicMock()
    emulator.wait_for_menu_ready = AsyncMock()
    events = (
        _event(1, TextEventKind.MENU_OPENED),
        _event(2, TextEventKind.MENU_CLOSED),
        _event(3, TextEventKind.MENU_OPENED),
    )

    assert (
        await drive_standard_dialog(
            emulator,
            stop_on=frozenset({TextEventKind.MENU_OPENED}),
            initial_events=events,
        )
        == ""
    )
    emulator.wait_for_text_events.assert_not_called()
    emulator.wait_for_menu_ready.assert_awaited_once_with()


@pytest.mark.unit
async def test_dialog_driver_waits_through_a_transition_marker() -> None:
    """Do not expose a closed interaction before its next rendered decision."""
    emulator = MagicMock()
    emulator.wait_until_ready = AsyncMock()

    assert (
        await drive_standard_dialog(
            emulator,
            stop_on=frozenset({TextEventKind.INTERACTION_CLOSED}),
            initial_events=(_event(1, TextEventKind.INTERACTION_CLOSED),),
        )
        == ""
    )
    emulator.wait_until_ready.assert_awaited_once_with()


def _event(
    sequence: int,
    kind: TextEventKind,
    page: DialogPage | None = None,
) -> TextEvent:
    return TextEvent(sequence=sequence, frame=1, kind=kind, page=page)
