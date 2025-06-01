from agent.base import BaseStateWithEmulator, BaseStoreWithEmulator
from agent.state import AgentState
from common.goals import Goals
from emulator.game_state import YellowLegacyGameState
from memory.agent_memory import AgentMemory


class TextHandlerState(BaseStateWithEmulator):
    """The state used in the text handler graph workflow."""

    iteration: int | None = None
    agent_memory: AgentMemory | None = None
    goals: Goals | None = None
    needs_generic_handling: bool | None = None

    def to_prompt_string(self, game_state: YellowLegacyGameState) -> str:
        """Get a string representation of the agent and game state to be used in prompts."""
        player_info = game_state.player_info
        return "\n\n".join((str(self.agent_memory), str(self.goals), str(player_info)))


class TextHandlerStore(BaseStoreWithEmulator[TextHandlerState]):
    """Concrete store for the text handler state."""

    async def set_state_from_parent(self, parent_state: AgentState) -> None:
        """Set the state from the parent state. Meant to be called at subflow initialization."""
        await self.set_state(
            {
                "iteration": parent_state.iteration,
                "agent_memory": parent_state.agent_memory,
                "goals": parent_state.goals,
            },
        )

    async def set_agent_memory(self, agent_memory: AgentMemory) -> None:
        """Set the agent memory."""
        await self.set_state({"agent_memory": agent_memory})

    async def set_needs_generic_handling(self, needs_generic_handling: bool) -> None:
        """Set the needs generic handling."""
        await self.set_state({"needs_generic_handling": needs_generic_handling})
