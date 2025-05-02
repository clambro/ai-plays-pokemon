import asyncio
from contextvars import ContextVar

from emulator.emulator import YellowLegacyEmulator

# Create a context variable to store the emulator instance
emulator_context: ContextVar[YellowLegacyEmulator | None] = ContextVar("emulator", default=None)


class EmulatorContext:
    """Async context manager for managing the emulator instance."""

    def __init__(self, rom_path: str, initial_state_path: str | None = None) -> None:
        self.rom_path = rom_path
        self.initial_state_path = initial_state_path
        self._emulator: YellowLegacyEmulator | None = None
        self._running = False
        self._tick_task: asyncio.Task | None = None

    async def __aenter__(self) -> "EmulatorContext":
        """Initialize the emulator and start the tick loop."""
        self._emulator = YellowLegacyEmulator(self.rom_path, self.initial_state_path)
        emulator_context.set(self._emulator)
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Stop the emulator and clean up resources."""
        self._running = False
        if self._tick_task:
            await self._tick_task
        self._cleanup()

    async def _tick_loop(self) -> None:
        """Continuously tick the emulator forward."""
        while self._running and self._emulator:
            if not self._emulator.tick():
                break
            await asyncio.sleep(0)  # Yield to other tasks.
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up the emulator and stop the tick loop."""
        self._running = False
        if self._emulator:
            self._emulator.stop()
            emulator_context.set(None)


def get_emulator() -> YellowLegacyEmulator:
    """Get the current emulator instance from the context."""
    emulator = emulator_context.get()
    if emulator is None:
        raise RuntimeError("No emulator instance available in the current context")
    return emulator
