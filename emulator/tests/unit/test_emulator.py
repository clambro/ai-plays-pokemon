"""Tests for the application-facing emulator."""

import asyncio

import pytest

import emulator.emulator as emulator_module
from emulator.emulator import YellowLegacyEmulator


@pytest.mark.unit
async def test_emulator_stops_worker_if_context_entry_is_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stop the worker if cancellation interrupts the startup grace period."""
    started = asyncio.Event()
    stopped = asyncio.Event()

    class FakePyBoyWorker:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def start(self) -> None:
            started.set()

        async def stop(self) -> None:
            stopped.set()

    monkeypatch.setattr(emulator_module, "PyBoyWorker", FakePyBoyWorker)
    emulator = YellowLegacyEmulator("test.gbc", mute_sound=True, headless=True)
    context_entry = asyncio.create_task(emulator.__aenter__())
    await started.wait()
    await asyncio.sleep(0)

    context_entry.cancel()

    with pytest.raises(asyncio.CancelledError):
        await context_entry
    assert stopped.is_set()
