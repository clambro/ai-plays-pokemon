from datetime import datetime, timedelta

from junjo import BaseState, BaseStore

from agent.state import AgentStore
from common.goals import Goals
from emulator.emulator import YellowLegacyEmulator
from memory.agent_memory import AgentMemory


class BattleHandlerState(BaseState):
    """The state used in the battle handler graph workflow."""

    iteration: int | None = None
    agent_memory: AgentMemory | None = None
    goals: Goals | None = None
    emulator_save_state: str | None = None
    last_emulator_save_state_time: datetime | None = None


class BattleHandlerStore(BaseStore[BattleHandlerState]):
    """Concrete store for the battle handler state."""

    @classmethod
    async def from_parent(cls, parent_store: AgentStore) -> "BattleHandlerStore":
        """Create a new store from the parent state."""
        parent_state = await parent_store.get_state()
        return cls(
            BattleHandlerState(
                iteration=parent_state.iteration,
                agent_memory=parent_state.agent_memory,
                goals=parent_state.goals,
                emulator_save_state=parent_state.emulator_save_state,
                last_emulator_save_state_time=parent_state.last_emulator_save_state_time,
            ),
        )

    async def set_agent_memory(self, agent_memory: AgentMemory) -> None:
        """Set the agent memory."""
        await self.set_state({"agent_memory": agent_memory})

    async def set_goals(self, goals: Goals) -> None:
        """Set the goals."""
        await self.set_state({"goals": goals})

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
