from datetime import datetime, timedelta
from pathlib import Path

from junjo import BaseState, BaseStore
from pydantic import BaseModel, Field

from common.enums import AgentStateHandler, Tool
from common.goals import Goals
from emulator.emulator import YellowLegacyEmulator
from memory.long_term_memory import LongTermMemory
from memory.raw_memory import RawMemory
from overworld_map.schemas import OverworldMap
from summary_memory.schemas import SummaryMemory


class AgentState(BaseState):
    """The state used in the agent graph workflow."""

    folder: Path
    iteration: int = 0
    raw_memory: RawMemory = Field(default_factory=RawMemory)
    summary_memory: SummaryMemory = Field(default_factory=SummaryMemory)
    long_term_memory: LongTermMemory = Field(default_factory=LongTermMemory)
    handler: AgentStateHandler | None = None
    current_map: OverworldMap | None = None
    goals: Goals = Field(default_factory=Goals)
    should_critique: bool = False
    tool: Tool | None = None
    tool_args: BaseModel | None = None
    emulator_save_state: str | None = None
    last_emulator_save_state_time: datetime | None = None


class AgentStore(BaseStore[AgentState]):
    """Concrete store for the agent state."""

    async def set_iteration(self, iteration: int) -> None:
        """Set the iteration."""
        await self.set_state({"iteration": iteration})

    async def set_raw_memory(self, raw_memory: RawMemory) -> None:
        """Set the raw memory."""
        await self.set_state({"raw_memory": raw_memory})

    async def set_summary_memory(self, summary_memory: SummaryMemory) -> None:
        """Set the summary memory."""
        await self.set_state({"summary_memory": summary_memory})

    async def set_long_term_memory(self, long_term_memory: LongTermMemory) -> None:
        """Set the long-term memory."""
        await self.set_state({"long_term_memory": long_term_memory})

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
