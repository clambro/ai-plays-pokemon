from pathlib import Path

from pydantic import Field

from agent.base import BaseStateWithEmulator, BaseStoreWithEmulator
from common.enums import AgentStateHandler
from common.goals import Goals
from memory.agent_memory import AgentMemory


class AgentState(BaseStateWithEmulator):
    """The state used in the agent graph workflow."""

    folder: Path
    iteration: int = 0
    agent_memory: AgentMemory = Field(default_factory=AgentMemory)
    handler: AgentStateHandler | None = None
    goals: Goals = Field(default_factory=Goals)


class AgentStore(BaseStoreWithEmulator[AgentState]):
    """Concrete store for the agent state."""

    async def set_iteration(self, iteration: int) -> None:
        """Set the iteration."""
        await self.set_state({"iteration": iteration})

    async def set_agent_memory(self, agent_memory: AgentMemory) -> None:
        """Set the agent memory."""
        await self.set_state({"agent_memory": agent_memory})

    async def set_handler(self, handler: AgentStateHandler | None) -> None:
        """Set the handler."""
        await self.set_state({"handler": handler})

    async def set_goals(self, goals: Goals) -> None:
        """Set the goals."""
        await self.set_state({"goals": goals})
