from datetime import datetime

from pydantic import BaseModel

from agent.base import BaseStateWithEmulator, BaseStoreWithEmulator
from agent.state import AgentState
from common.enums import Tool
from common.goals import Goals
from memory.agent_memory import AgentMemory
from overworld_map.schemas import OverworldMap


class OverworldHandlerState(BaseStateWithEmulator):
    """The state used in the overworld handler graph workflow."""

    iteration: int | None = None
    agent_memory: AgentMemory | None = None
    goals: Goals | None = None
    current_map: OverworldMap | None = None
    should_critique: bool | None = None
    tool: Tool | None = None
    tool_args: BaseModel | None = None
    emulator_save_state: str | None = None
    last_emulator_save_state_time: datetime | None = None
    needs_generic_handling: bool | None = None


class OverworldHandlerStore(BaseStoreWithEmulator[OverworldHandlerState]):
    """Concrete store for the overworld handler state."""

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

    async def set_current_map(self, current_map: OverworldMap) -> None:
        """Set the current map."""
        await self.set_state({"current_map": current_map})

    async def set_should_critique(self, should_critique: bool) -> None:
        """Set the should critique."""
        await self.set_state({"should_critique": should_critique})

    async def set_tool(self, tool: Tool | None) -> None:
        """Set the tool."""
        await self.set_state({"tool": tool})

    async def set_tool_args(self, tool_args: BaseModel | None) -> None:
        """Set the tool args."""
        await self.set_state({"tool_args": tool_args})
