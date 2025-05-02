import asyncio
from pathlib import Path
from typing import ClassVar, Any
from threading import Lock

from pyboy import PyBoy
from constants import GAME_TICKS_PER_SECOND
from emulator.game_state import YellowLegacyGameState


class YellowLegacyEmulator:
    """
    Wrapper for accessing the game state of Pokemon Yellow Legacy. Encapsulates the PyBoy API so
    that the rest of the codebase doesn't need to worry about emulation or memory addresses.
    """

    _instance: ClassVar["YellowLegacyEmulator | None"] = None
    _lock: ClassVar[Lock] = Lock()
    tick_num: int = 0
    _pyboy: PyBoy
    _game_state: YellowLegacyGameState

    def __new__(cls, *args: Any, **kwargs: Any) -> "YellowLegacyEmulator":
        """Singleton pattern with thread safety."""
        with cls._lock:
            if cls._instance is not None:
                return cls._instance
            cls._instance = super().__new__(cls)
            cls._instance._initialize(*args, **kwargs)
            return cls._instance

    @classmethod
    def _initialize(cls, rom_path: str, initial_state_path: str | None = None) -> None:
        """Initialize the emulator."""
        cls.tick_num = 0
        cls._pyboy = PyBoy(rom_path)
        if initial_state_path:
            with Path(initial_state_path).open("rb") as f:
                cls._pyboy.load_state(f)

        cls._game_state = YellowLegacyGameState.from_memory(cls._pyboy.memory, cls.tick_num)

    @classmethod
    def get_game_state(cls) -> YellowLegacyGameState:
        """
        Get the current game state, lazily updating it if necessary.

        :return: The current game state.
        """
        if not cls._instance:
            raise RuntimeError("Emulator not initialized")
        if cls.tick_num != cls._game_state.tick_num:
            cls._game_state = YellowLegacyGameState.from_memory(cls._pyboy.memory, cls.tick_num)
        return cls._game_state

    @classmethod
    def tick(cls, count: int = 1) -> bool:
        """
        Tick the emulator forward by `count` frames.

        :param count: Number of frames to tick forward.
        :return: Whether the game is still running.
        """
        if not cls._instance:
            raise RuntimeError("Emulator not initialized")
        cls.tick_num += count
        return cls._pyboy.tick(count, render=True, sound=True)

    @classmethod
    async def async_tick_indefinitely(cls) -> None:
        """Tick the emulator indefinitely on its own thread."""
        if not cls._instance:
            raise RuntimeError("Emulator not initialized")
        while True:
            if not cls.tick():
                cls.stop()
                break
            await asyncio.sleep(0)  # Return control to the event loop.

    @classmethod
    def stop(cls) -> None:
        """Stop the emulator."""
        if not cls._instance:
            raise RuntimeError("Emulator not initialized")
        cls._pyboy.stop()
        cls._instance = None

    @classmethod
    def get_screenshot_bytes(cls) -> bytes:
        """Get a screenshot of the current game screen as a bytes object."""
        if not cls._instance:
            raise RuntimeError("Emulator not initialized")
        img = cls._pyboy.screen.image
        if img is None:
            raise RuntimeError("No screenshot available")
        return img.tobytes()

    @classmethod
    async def press_buttons(cls, buttons: list[str], delay_frames: int = 20) -> None:
        """Press the buttons in order, with a delay between each."""
        if not cls._instance:
            raise RuntimeError("Emulator not initialized")
        for button in buttons:
            cls._pyboy.button(button, delay_frames)
            await asyncio.sleep(delay_frames / GAME_TICKS_PER_SECOND)
