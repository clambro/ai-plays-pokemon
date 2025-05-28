from agent.nodes.critique.prompts import CRITIQUE_PROMPT
from agent.nodes.critique.schemas import CritiqueResponse
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from memory.agent_memory import AgentMemory
from memory.raw_memory import RawMemoryPiece
from overworld_map.schemas import OverworldMap


class CritiqueService:
    """A service that critiques the current state of the game."""

    def __init__(
        self,
        iteration: int,
        agent_memory: AgentMemory,
        current_map: OverworldMap,
        goals: Goals,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.agent_memory = agent_memory
        self.current_map = current_map
        self.goals = goals
        self.emulator = emulator
        self.llm_service = GeminiLLMService(GeminiLLMEnum.PRO)

    async def critique(self) -> AgentMemory:
        """Critique the current state of the game."""
        game_state = self.emulator.get_game_state()
        screenshot = self.emulator.get_screenshot()
        prompt = CRITIQUE_PROMPT.format(
            player_info=game_state.player_info,
            current_map=self.current_map.to_string(game_state),
            goals=self.goals,
            agent_memory=self.agent_memory,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            [screenshot, prompt],
            schema=CritiqueResponse,
            thinking_tokens=512,
        )
        self.agent_memory.append_raw_memory(
            RawMemoryPiece(
                iteration=self.iteration,
                content=(
                    f"An exterior critic model has provided you with the following advice on your"
                    f" progress. This is useful, high-quality information: {response.critique}"
                ),
            ),
        )

        return self.agent_memory
