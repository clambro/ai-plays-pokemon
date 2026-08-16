"""Unit tests for core text-event logic."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.enums import Button, MapId
from emulator.control_events import ControlBoundary, ControlResult
from emulator.text_events import (
    CompletedSpriteInteraction,
    DialogPage,
    SpriteInteractionTarget,
    TextEvent,
    TextEventJournal,
    TextEventKind,
    TextEventReducer,
    TextEventSnapshot,
    drive_standard_dialog,
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
    reducer = TextEventReducer()
    first_page = DialogPage(top_line="VOLTAIL used", bottom_line="THUNDERSHOCK!")
    scrolled_page = DialogPage(top_line="THUNDERSHOCK!", bottom_line="It's effective!")
    events = [
        _event(1, TextEventKind.PAGE_COMPLETED, first_page),
        _event(2, TextEventKind.AUTOMATIC_SCROLL, first_page),
        _event(3, TextEventKind.PAGE_COMPLETED, scrolled_page),
        _event(4, TextEventKind.INTERACTION_CLOSED),
        _event(5, TextEventKind.PAGE_COMPLETED, scrolled_page),
    ]

    assert reducer.reduce(events) == (
        "VOLTAIL used THUNDERSHOCK! It's effective! THUNDERSHOCK! It's effective!"
    )


@pytest.mark.unit
def test_reducer_preserves_scroll_context_across_event_batches() -> None:
    """Remove cross-batch overlap without suppressing a later interaction."""
    reducer = TextEventReducer()
    first_page = DialogPage(top_line="OAK: Whew...", bottom_line="A POKéMON can appear")
    scrolled_page = DialogPage(
        top_line="A POKéMON can appear",
        bottom_line="anytime in tall grass!",
    )

    assert reducer.reduce([_event(1, TextEventKind.INPUT_REQUIRED, first_page)]) == (
        "OAK: Whew... A POKéMON can appear"
    )
    assert reducer.reduce([_event(2, TextEventKind.INPUT_REQUIRED, scrolled_page)]) == (
        "anytime in tall grass!"
    )
    assert reducer.reduce([_event(3, TextEventKind.INTERACTION_CLOSED)]) == ""
    assert reducer.reduce([_event(4, TextEventKind.INPUT_REQUIRED, scrolled_page)]) == (
        "A POKéMON can appear anytime in tall grass!"
    )


@pytest.mark.unit
def test_reducer_attributes_complete_literal_dialog_to_its_map_sprite() -> None:
    """Retain one sprite interaction across event batches until its ROM close boundary."""
    reducer = TextEventReducer()
    target = SpriteInteractionTarget(map_id=MapId.MT_MOON_B2F, sprite_id=7)
    first_page = DialogPage(top_line="You want the", bottom_line="HELIX FOSSIL?")
    second_page = DialogPage(top_line="HELIX FOSSIL?", bottom_line="Then this is mine!")

    assert (
        reducer.reduce(
            [
                _event(
                    1,
                    TextEventKind.SPRITE_INTERACTION_STARTED,
                    sprite_target=target,
                ),
                _event(2, TextEventKind.INPUT_REQUIRED, first_page),
            ]
        )
        == "You want the HELIX FOSSIL?"
    )
    assert reducer.drain_completed_sprite_interactions() == ()

    assert (
        reducer.reduce(
            [
                _event(3, TextEventKind.INPUT_REQUIRED, second_page),
                _event(4, TextEventKind.INTERACTION_CLOSED),
            ]
        )
        == "Then this is mine!"
    )
    assert reducer.drain_completed_sprite_interactions() == (
        CompletedSpriteInteraction(
            target=target,
            text="You want the HELIX FOSSIL? Then this is mine!",
        ),
    )
    assert reducer.drain_completed_sprite_interactions() == ()


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
            reducer=TextEventReducer(),
            stop_on=frozenset({TextEventKind.MENU_OPENED}),
            initial_snapshot=TextEventSnapshot(events=events),
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
            reducer=TextEventReducer(),
            stop_on=frozenset({TextEventKind.INTERACTION_CLOSED}),
            initial_snapshot=TextEventSnapshot(
                events=(_event(1, TextEventKind.INTERACTION_CLOSED),)
            ),
        )
        == ""
    )
    emulator.wait_until_ready.assert_awaited_once_with()


@pytest.mark.unit
async def test_dialog_driver_uses_live_boundary_after_input_event_was_claimed() -> None:
    """Advance text when the preceding domain already claimed its input event."""
    emulator = MagicMock()
    emulator.wait_for_text_events = AsyncMock(
        return_value=(_event(1, TextEventKind.INTERACTION_CLOSED),)
    )
    emulator.pulse_button = AsyncMock()
    emulator.wait_until_ready = AsyncMock(
        return_value=ControlResult(boundary=ControlBoundary.OVERWORLD_READY)
    )

    await drive_standard_dialog(
        emulator,
        reducer=TextEventReducer(),
        stop_on=frozenset({TextEventKind.INTERACTION_CLOSED}),
        initial_snapshot=TextEventSnapshot(
            boundary=ControlBoundary.TEXT_INPUT_READY,
        ),
    )

    emulator.pulse_button.assert_awaited_once_with(Button.A)


@pytest.mark.unit
async def test_dialog_driver_hands_off_when_input_opens_a_custom_interface() -> None:
    """Stop waiting for text events once the ROM exposes another ready interface."""
    emulator = MagicMock()
    emulator.wait_until_ready = AsyncMock(
        return_value=ControlResult(boundary=ControlBoundary.INTERACTIVE_READY)
    )
    emulator.drain_text_events.return_value = ()
    page = DialogPage(top_line="Take your time.", bottom_line="")

    transcript = await drive_standard_dialog(
        emulator,
        reducer=TextEventReducer(),
        stop_on=frozenset({TextEventKind.INTERACTION_CLOSED}),
        initial_snapshot=TextEventSnapshot(
            events=(
                _event(1, TextEventKind.PAGE_COMPLETED, page),
                _event(2, TextEventKind.INPUT_RESOLVED),
            ),
        ),
    )

    assert transcript == "Take your time."
    emulator.wait_until_ready.assert_awaited_once_with()
    emulator.wait_for_text_events.assert_not_called()


def _event(
    sequence: int,
    kind: TextEventKind,
    page: DialogPage | None = None,
    *,
    sprite_target: SpriteInteractionTarget | None = None,
) -> TextEvent:
    return TextEvent(
        sequence=sequence,
        frame=1,
        kind=kind,
        page=page,
        sprite_target=sprite_target,
    )
