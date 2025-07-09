from junjo import BaseState, BaseStore

from agent.state import AgentState
from agent.subflows.overworld_handler.enums import OverworldTool
from emulator.game_state import YellowLegacyGameState
from memory.goals import Goals
from memory.long_term_memory import LongTermMemory
from memory.raw_memory import RawMemory
from memory.summary_memory import SummaryMemory
from overworld_map.schemas import OverworldMap


class OverworldHandlerState(BaseState):
    """The state used in the overworld handler graph workflow."""

    iteration: int | None = None
    raw_memory: RawMemory | None = None
    summary_memory: SummaryMemory | None = None
    long_term_memory: LongTermMemory | None = None
    goals: Goals | None = None
    current_map: OverworldMap | None = None
    tool: OverworldTool | None = None
    iterations_since_last_critique: int | None = None

    def to_prompt_string(self, game_state: YellowLegacyGameState) -> str:
        """Get a string representation of the agent and game state to be used in prompts."""
        if self.current_map is None:
            raise ValueError("Current map is not set")
        return "\n\n".join(
            (
                str(self.raw_memory),
                str(self.summary_memory),
                str(self.long_term_memory),
                str(self.goals),
                self.current_map.to_string(game_state),
                game_state.player_info,
            ),
        )


class OverworldHandlerStore(BaseStore[OverworldHandlerState]):
    """Concrete store for the overworld handler state."""

    async def set_state_from_parent(self, parent_state: AgentState) -> None:
        """Set the state from the parent state. Meant to be called at subflow initialization."""
        await self.set_state(
            {
                "iteration": parent_state.iteration,
                "raw_memory": parent_state.raw_memory,
                "summary_memory": parent_state.summary_memory,
                "long_term_memory": parent_state.long_term_memory,
                "goals": parent_state.goals,
                "iterations_since_last_critique": parent_state.iterations_since_last_critique,
            },
        )

    async def set_raw_memory(self, raw_memory: RawMemory) -> None:
        """Set the raw memory."""
        await self.set_state({"raw_memory": raw_memory})

    async def set_current_map(self, current_map: OverworldMap) -> None:
        """Set the current map."""
        await self.set_state({"current_map": current_map})

    async def set_tool(self, tool: OverworldTool | None) -> None:
        """Set the tool."""
        await self.set_state({"tool": tool})

    async def set_iterations_since_last_critique(self, iterations_since_last_critique: int) -> None:
        """Set the iterations since the last critique."""
        await self.set_state({"iterations_since_last_critique": iterations_since_last_critique})
