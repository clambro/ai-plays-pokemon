from agent.nodes.critique.prompts import CRITIQUE_PROMPT
from agent.nodes.critique.schemas import CritiqueResponse
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from long_term_memory.schemas import LongTermMemory
from overworld_map.schemas import OverworldMap
from raw_memory.schemas import RawMemory, RawMemoryPiece
from summary_memory.schemas import SummaryMemory


class CritiqueService:
    """A service that critiques the current state of the game."""

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        current_map: OverworldMap,
        goals: Goals,
        emulator: YellowLegacyEmulator,
        summary_memory: SummaryMemory,
        long_term_memory: LongTermMemory,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.current_map = current_map
        self.goals = goals
        self.emulator = emulator
        self.summary_memory = summary_memory
        self.long_term_memory = long_term_memory
        self.llm_service = GeminiLLMService(GeminiLLMEnum.PRO)

    async def critique(self) -> None:
        """Critique the current state of the game."""
        game_state = self.emulator.get_game_state()
        screenshot = self.emulator.get_screenshot()
        prompt = CRITIQUE_PROMPT.format(
            player_info=game_state.player_info,
            current_map=self.current_map.to_string(game_state),
            goals=self.goals,
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            long_term_memory=self.long_term_memory,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            [screenshot, prompt],
            schema=CritiqueResponse,
            thinking_tokens=512,
        )
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=(
                    f"An exterior critic model has provided you with the following advice on your"
                    f" progress. This is CRITICAL, HIGH QUALITY INFORMATION: {response.critique}"
                ),
            ),
        )
