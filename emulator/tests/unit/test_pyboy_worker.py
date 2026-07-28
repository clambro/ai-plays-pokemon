"""Tests for the PyBoy worker."""

import asyncio
from threading import Event, get_ident
from typing import TYPE_CHECKING

import pytest

import emulator.pyboy_worker as worker_module
from common.enums import Button
from emulator.pyboy_worker import PyBoyWorker

if TYPE_CHECKING:
    from collections.abc import Callable


class _FakePyBoy:
    def __init__(self, calls: list[tuple[str, int]]) -> None:
        self.calls = calls
        self.buttons: list[tuple[Button, int]] = []
        self._record("construct")

    @property
    def memory(self) -> object:
        self._record("memory")
        return object()

    def tick(self, count: int, *, render: bool, sound: bool) -> bool:
        assert (count, render, sound) == (1, True, True)
        self._record("tick")
        return True

    def button(self, button: Button, hold_frames: int) -> None:
        self._record("button")
        self.buttons.append((button, hold_frames))

    def stop(self) -> None:
        self._record("stop")

    def _record(self, operation: str) -> None:
        self.calls.append((operation, get_ident()))


@pytest.mark.unit
async def test_worker_owns_pyboy_and_executes_commands_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run construction, commands, ticks, and shutdown on one owner thread."""
    calls: list[tuple[str, int]] = []
    instances: list[_FakePyBoy] = []

    def create_pyboy(*args: object, **kwargs: object) -> _FakePyBoy:
        assert args == ("test.gbc",)
        assert kwargs == {"sound_volume": 0, "window": "null"}
        pyboy = _FakePyBoy(calls)
        instances.append(pyboy)
        return pyboy

    monkeypatch.setattr(worker_module, "PyBoy", create_pyboy)
    worker = _create_worker()
    await worker.start()

    memory = await worker.execute(lambda pyboy: pyboy.memory)
    await worker.execute(lambda pyboy: pyboy.button(Button.A, 10))
    await worker.execute(lambda pyboy: pyboy.button(Button.B, 2))
    await worker.stop()

    assert memory is not None
    assert len(instances) == 1
    assert instances[0].buttons == [(Button.A, 10), (Button.B, 2)]
    owner_thread_ids = {thread_id for _, thread_id in calls}
    assert len(owner_thread_ids) == 1
    assert get_ident() not in owner_thread_ids


@pytest.mark.unit
@pytest.mark.parametrize(
    ("headless", "expected_window", "uses_headless_delay"),
    [
        (False, "SDL2", False),
        (True, "null", True),
    ],
)
async def test_worker_only_applies_extra_tick_delay_when_headless(
    monkeypatch: pytest.MonkeyPatch,
    *,
    headless: bool,
    expected_window: str,
    uses_headless_delay: bool,
) -> None:
    """Leave SDL pacing to PyBoy while keeping headless execution bounded."""
    calls: list[tuple[str, int]] = []
    tick_started = Event()
    sleep_durations = []

    class TickTrackingPyBoy(_FakePyBoy):
        def tick(self, count: int, *, render: bool, sound: bool) -> bool:
            tick_started.set()
            return super().tick(count, render=render, sound=sound)

    def create_pyboy(*args: object, **kwargs: object) -> TickTrackingPyBoy:
        assert args == ("test.gbc",)
        assert kwargs == {"sound_volume": 0, "window": expected_window}
        return TickTrackingPyBoy(calls)

    monkeypatch.setattr(worker_module, "PyBoy", create_pyboy)
    monkeypatch.setattr(worker_module.time, "sleep", sleep_durations.append)
    worker = _create_worker(headless=headless)
    await worker.start()
    assert tick_started.wait(timeout=1)
    await worker.stop()

    assert bool(sleep_durations) is uses_headless_delay


@pytest.mark.unit
async def test_worker_propagates_unexpected_tick_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expose owner-thread failure to a pending command without hanging."""
    tick_started = Event()
    release_tick = Event()

    class FailingPyBoy(_FakePyBoy):
        def tick(self, count: int, *, render: bool, sound: bool) -> bool:
            super().tick(count, render=render, sound=sound)
            tick_started.set()
            release_tick.wait(timeout=1)
            raise RuntimeError("tick failed")

    monkeypatch.setattr(
        worker_module,
        "PyBoy",
        _fake_pyboy_factory(FailingPyBoy),
    )
    worker = _create_worker()
    await worker.start()
    assert tick_started.wait(timeout=1)
    pending_command = asyncio.create_task(worker.execute(lambda pyboy: pyboy.memory))
    await asyncio.sleep(0)
    release_tick.set()

    with pytest.raises(RuntimeError, match="tick failed"):
        await pending_command
    with pytest.raises(RuntimeError, match="tick failed"):
        await worker.stop()


@pytest.mark.unit
async def test_worker_propagates_startup_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expose PyBoy construction failure and terminate the owner thread."""

    def fail_to_create(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("startup failed")

    monkeypatch.setattr(worker_module, "PyBoy", fail_to_create)

    with pytest.raises(RuntimeError, match="startup failed"):
        await _create_worker().start()


@pytest.mark.unit
async def test_worker_stops_if_startup_is_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop and join the owner thread when its startup waiter is cancelled."""
    calls: list[tuple[str, int]] = []
    creation_started = Event()
    release_creation = Event()

    def create_pyboy(*_args: object, **_kwargs: object) -> _FakePyBoy:
        creation_started.set()
        release_creation.wait(timeout=1)
        return _FakePyBoy(calls)

    monkeypatch.setattr(worker_module, "PyBoy", create_pyboy)
    worker = _create_worker()
    startup = asyncio.create_task(worker.start())
    await asyncio.sleep(0)
    assert creation_started.wait(timeout=1)

    startup.cancel()
    release_creation.set()

    with pytest.raises(asyncio.CancelledError):
        await startup
    assert not worker._thread.is_alive()
    assert [operation for operation, _ in calls] == ["construct", "stop"]


@pytest.mark.unit
async def test_worker_finishes_shutdown_before_propagating_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stop and join the owner thread before propagating shutdown cancellation."""
    stop_started = Event()
    release_stop = Event()

    class SlowStoppingPyBoy(_FakePyBoy):
        def stop(self) -> None:
            super().stop()
            stop_started.set()
            release_stop.wait(timeout=1)

    monkeypatch.setattr(
        worker_module,
        "PyBoy",
        _fake_pyboy_factory(SlowStoppingPyBoy),
    )
    worker = _create_worker()
    await worker.start()
    shutdown = asyncio.create_task(worker.stop())
    await asyncio.sleep(0)
    assert stop_started.wait(timeout=1)

    shutdown.cancel()
    release_stop.set()

    with pytest.raises(asyncio.CancelledError):
        await shutdown
    assert not worker._thread.is_alive()


def _create_worker(*, headless: bool = True) -> PyBoyWorker:
    return PyBoyWorker(
        "test.gbc",
        None,
        None,
        mute_sound=True,
        headless=headless,
    )


def _fake_pyboy_factory(
    fake_type: type[_FakePyBoy],
) -> Callable[..., _FakePyBoy]:
    calls: list[tuple[str, int]] = []

    def create(*_args: object, **_kwargs: object) -> _FakePyBoy:
        return fake_type(calls)

    return create
