"""Unit tests for core text-event logic."""

import asyncio

import pytest

from emulator.text_events import (
    DialogPage,
    TextEvent,
    TextEventJournal,
    TextEventKind,
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


def _event(
    sequence: int,
    kind: TextEventKind,
    page: DialogPage | None = None,
) -> TextEvent:
    return TextEvent(sequence=sequence, frame=1, kind=kind, page=page)
