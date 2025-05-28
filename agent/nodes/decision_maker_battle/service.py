from loguru import logger

from agent.nodes.decision_maker_battle.prompts import DECISION_MAKER_BATTLE_PROMPT
from agent.nodes.decision_maker_battle.schemas import DecisionMakerBattleResponse
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from memory.agent_memory import AgentMemory
from memory.raw_memory import RawMemoryPiece


class DecisionMakerBattleService:
    """A service that makes decisions based on the current game state in the battle."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        agent_memory: AgentMemory,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)
        self.agent_memory = agent_memory

    async def make_decision(self) -> AgentMemory:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = self.emulator.get_screenshot()
        prompt = DECISION_MAKER_BATTLE_PROMPT.format(agent_memory=self.agent_memory)
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=DecisionMakerBattleResponse,
            )
            self.agent_memory.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=str(response),
                ),
            )
            await self.emulator.press_buttons([response.button])
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")

        return self.agent_memory
