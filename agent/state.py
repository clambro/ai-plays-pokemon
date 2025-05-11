from pathlib import Path

from pydantic import Field

from common.enums import AgentStateHandler
from common.goals import Goals
from emulator.enums import Button
from overworld_map.schemas import OverworldMap
from raw_memory.schemas import RawMemory
from junjo.state import BaseState
from junjo.store import BaseStore


class AgentState(BaseState):
    """The state used in the agent graph workflow."""

    folder: Path
    iteration: int = 0
    raw_memory: RawMemory = Field(default_factory=RawMemory)
    handler: AgentStateHandler | None = None
    current_map: OverworldMap | None = None
    goals: Goals = Field(default_factory=Goals)


class AgentStore(BaseStore[AgentState]):
    """Concrete store for the agent state."""

    async def set_iteration(self, iteration: int) -> None:
        """Set the iteration."""
        await self.set_state({"iteration": iteration})

    async def set_raw_memory(self, raw_memory: RawMemory) -> None:
        """Set the raw memory."""
        await self.set_state({"raw_memory": raw_memory})

    async def set_handler(self, handler: AgentStateHandler | None) -> None:
        """Set the handler."""
        await self.set_state({"handler": handler})

    async def set_current_map(self, current_map: OverworldMap) -> None:
        """Set the current map."""
        await self.set_state({"current_map": current_map})

    async def set_goals(self, goals: Goals) -> None:
        """Set the goals."""
        await self.set_state({"goals": goals})
