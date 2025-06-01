from pathlib import Path

from pydantic import Field

from agent.base import BaseStateWithEmulator, BaseStoreWithEmulator
from common.enums import AgentStateHandler
from common.goals import Goals
from emulator.game_state import YellowLegacyGameState
from memory.agent_memory import AgentMemory
from memory.long_term_memory import LongTermMemory
from memory.raw_memory import RawMemory
from memory.summary_memory import SummaryMemory


class AgentState(BaseStateWithEmulator):
    """The state used in the agent graph workflow."""

    folder: Path
    iteration: int = 0
    agent_memory: AgentMemory = Field(default_factory=AgentMemory)
    raw_memory: RawMemory = Field(default_factory=RawMemory)
    summary_memory: SummaryMemory = Field(default_factory=SummaryMemory)
    long_term_memory: LongTermMemory = Field(default_factory=LongTermMemory)
    goals: Goals = Field(default_factory=Goals)
    handler: AgentStateHandler | None = None

    def to_prompt_string(self, game_state: YellowLegacyGameState) -> str:
        """Get a string representation of the agent and game state to be used in prompts."""
        return "\n\n".join(
            (
                str(self.raw_memory),
                str(self.summary_memory),
                str(self.long_term_memory),
                str(self.goals),
                game_state.player_info,
            ),
        )


class AgentStore(BaseStoreWithEmulator[AgentState]):
    """Concrete store for the agent state."""

    async def set_iteration(self, iteration: int) -> None:
        """Set the iteration."""
        await self.set_state({"iteration": iteration})

    async def set_agent_memory(self, agent_memory: AgentMemory) -> None:
        """Set the agent memory."""
        await self.set_state({"agent_memory": agent_memory})

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

    async def set_goals(self, goals: Goals) -> None:
        """Set the goals."""
        await self.set_state({"goals": goals})
