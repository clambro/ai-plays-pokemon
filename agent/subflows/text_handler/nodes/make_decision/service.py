from loguru import logger

from agent.subflows.text_handler.nodes.make_decision.prompts import DECISION_MAKER_TEXT_PROMPT
from agent.subflows.text_handler.nodes.make_decision.schemas import DecisionMakerTextResponse
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilder
from emulator.emulator import YellowLegacyEmulator
from memory.agent_memory import AgentMemory
from memory.raw_memory import RawMemoryPiece


class DecisionMakerTextService:
    """A service that makes decisions based on the current game state in the text."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

    def __init__(
        self,
        iteration: int,
        agent_memory: AgentMemory,
        state_string_builder: StateStringBuilder,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.agent_memory = agent_memory
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def make_decision(self) -> AgentMemory:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = self.emulator.get_screenshot()
        game_state = self.emulator.get_game_state()
        state_string = self.state_string_builder(game_state)
        prompt = DECISION_MAKER_TEXT_PROMPT.format(
            state=state_string,
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
