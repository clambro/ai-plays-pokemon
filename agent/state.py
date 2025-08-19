from pathlib import Path
from typing import Literal

from junjo import BaseState, BaseStore
from pydantic import Field

from agent.enums import AgentStateHandler
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from memory.goals import Goals
from memory.long_term_memory import LongTermMemory
from memory.raw_memory import RawMemory
from memory.summary_memory import SummaryMemory


class AgentState(BaseState):
    """The state used in the agent graph workflow."""

    folder: Path
    iteration: int = 0
    iterations_since_last_critique: int = 0
    iterations_since_last_ltm_retrieval: int = 0
    raw_memory: RawMemory = Field(default_factory=RawMemory)
    summary_memory: SummaryMemory = Field(default_factory=SummaryMemory)
    long_term_memory: LongTermMemory = Field(default_factory=LongTermMemory)
    goals: Goals = Field(default_factory=Goals)
    handler: AgentStateHandler | None = None
    previous_handler: AgentStateHandler | None = None
    should_retrieve_memory: bool | None = None
    should_critique: bool | None = None
    emulator_save_state: str | None = None

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

    async def set_goals(self, goals: Goals) -> None:
        """Set the goals."""
        await self.set_state({"goals": goals})

    async def set_handler(self, handler: AgentStateHandler) -> None:
        """Set the handler."""
        await self.set_state({"handler": handler})

    async def set_previous_handler(self, previous_handler: AgentStateHandler | None) -> None:
        """Set the previous handler."""
        await self.set_state({"previous_handler": previous_handler})

    async def set_should_retrieve_memory(
        self,
        should_retrieve_memory: Literal[True, False],
    ) -> None:
        """Set the should retrieve memory."""
        await self.set_state({"should_retrieve_memory": should_retrieve_memory})

    async def set_should_critique(self, should_critique: Literal[True, False]) -> None:
        """Set the should critique."""
        await self.set_state({"should_critique": should_critique})

    async def set_iterations_since_last_critique(self, iterations_since_last_critique: int) -> None:
        """Set the iterations since the last critique."""
        await self.set_state({"iterations_since_last_critique": iterations_since_last_critique})

    async def set_iterations_since_last_ltm_retrieval(
        self,
        iterations_since_last_ltm_retrieval: int,
    ) -> None:
        """Set the iterations since the last long-term memory retrieval."""
        await self.set_state(
            {"iterations_since_last_ltm_retrieval": iterations_since_last_ltm_retrieval}
        )

    async def set_emulator_save_state_from_emulator(self, emulator: YellowLegacyEmulator) -> None:
        """
        Set the emulator save state from the emulator. Do this sparingly. Saving takes about two
        frames, so doing it too often messes with the game's audio, and it also hammers the
        telemetry.
        """
        await self.set_state({"emulator_save_state": await emulator.get_emulator_save_state()})
