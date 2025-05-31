from datetime import datetime, timedelta
from typing import TypeVar

from junjo import BaseState, BaseStore

from emulator.emulator import YellowLegacyEmulator


class BaseStateWithEmulator(BaseState):
    """
    Base state with emulator save state attributes. Should default to None in subclasses. If you
    forget to set these in a subclass, the type checker will catch it.
    """

    emulator_save_state: str | None
    last_emulator_save_state_time: datetime | None


_StateWithEmulatorT = TypeVar("_StateWithEmulatorT", bound=BaseStateWithEmulator)


class BaseStoreWithEmulator(BaseStore[_StateWithEmulatorT]):
    """Base store with emulator save state functionality."""

    async def set_emulator_save_state_from_emulator(self, emulator: YellowLegacyEmulator) -> None:
        """
        Set the emulator save state from the emulator, as long as it's been at least 1 second since
        the last save. Saving takes about two frames, so doing it too often messes with the game's
        audio.
        """
        now = datetime.now()
        state = await self.get_state()
        last_save_state_time = state.last_emulator_save_state_time
        if last_save_state_time and now - last_save_state_time < timedelta(seconds=1):
            return
        await self.set_state({"emulator_save_state": await emulator.get_emulator_save_state()})
        await self.set_state({"last_emulator_save_state_time": now})
