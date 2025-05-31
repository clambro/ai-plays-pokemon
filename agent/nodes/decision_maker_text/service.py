from loguru import logger

from agent.nodes.decision_maker_text.prompts import DECISION_MAKER_TEXT_PROMPT
from agent.nodes.decision_maker_text.schemas import DecisionMakerTextResponse
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from memory.agent_memory import AgentMemory
from memory.raw_memory import RawMemoryPiece


class DecisionMakerTextService:
    """A service that makes decisions based on the current game state in the text."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        agent_memory: AgentMemory,
        goals: Goals,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)
        self.agent_memory = agent_memory
        self.goals = goals

    async def make_decision(self) -> AgentMemory:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = self.emulator.get_screenshot()
        game_state = self.emulator.get_game_state()
        prompt = DECISION_MAKER_TEXT_PROMPT.format(
            agent_memory=self.agent_memory,
            goals=self.goals,
            player_info=game_state.player_info,
            text=game_state.get_on_screen_text(),
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=DecisionMakerTextResponse,
            )
            self.agent_memory.append_raw_memory(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=str(response),
                ),
            )
            await self.emulator.press_buttons([response.button])
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")

        return self.agent_memory
