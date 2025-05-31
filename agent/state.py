from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from agent.base import BaseStateWithEmulator, BaseStoreWithEmulator
from common.enums import AgentStateHandler, Tool
from common.goals import Goals
from memory.agent_memory import AgentMemory
from overworld_map.schemas import OverworldMap


class AgentState(BaseStateWithEmulator):
    """The state used in the agent graph workflow."""

    folder: Path
    iteration: int = 0
    agent_memory: AgentMemory = Field(default_factory=AgentMemory)
    handler: AgentStateHandler | None = None
    current_map: OverworldMap | None = None
    goals: Goals = Field(default_factory=Goals)
    should_critique: bool = False
    tool: Tool | None = None
    tool_args: BaseModel | None = None
    emulator_save_state: str | None = None
    last_emulator_save_state_time: datetime | None = None


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

    async def set_current_map(self, current_map: OverworldMap | None) -> None:
        """Set the current map."""
        await self.set_state({"current_map": current_map})

    async def set_goals(self, goals: Goals) -> None:
        """Set the goals."""
        await self.set_state({"goals": goals})

    async def set_should_critique(self, should_critique: bool) -> None:
        """Set the should critique."""
        await self.set_state({"should_critique": should_critique})

    async def set_tool(self, tool: Tool | None) -> None:
        """Set the tool."""
        await self.set_state({"tool": tool})

    async def set_tool_args(self, tool_args: BaseModel | None) -> None:
        """Set the tool args."""
        await self.set_state({"tool_args": tool_args})
