from datetime import datetime, timedelta

from junjo import BaseState, BaseStore

from agent.state import AgentState
from common.goals import Goals
from emulator.emulator import YellowLegacyEmulator
from memory.agent_memory import AgentMemory


class TextHandlerState(BaseState):
    """The state used in the text handler graph workflow."""

    iteration: int | None = None
    agent_memory: AgentMemory | None = None
    goals: Goals | None = None
    emulator_save_state: str | None = None
    last_emulator_save_state_time: datetime | None = None
    needs_generic_handling: bool | None = None


class TextHandlerStore(BaseStore[TextHandlerState]):
    """Concrete store for the text handler state."""

    async def set_state_from_parent(self, parent_state: AgentState) -> None:
        """Set the state from the parent state. Meant to be called at subflow initialization."""
        await self.set_state(
            {
                "iteration": parent_state.iteration,
                "agent_memory": parent_state.agent_memory,
                "goals": parent_state.goals,
                "emulator_save_state": parent_state.emulator_save_state,
                "last_emulator_save_state_time": parent_state.last_emulator_save_state_time,
            },
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

    async def set_needs_generic_handling(self, needs_generic_handling: bool) -> None:
        """Set the needs generic handling."""
        await self.set_state({"needs_generic_handling": needs_generic_handling})
