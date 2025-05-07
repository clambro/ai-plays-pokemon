from datetime import datetime
from agent.actions.decision_maker_overworld.prompts import DECISION_MAKER_OVERWORLD_PROMPT
from agent.actions.decision_maker_overworld.schemas import DecisionMakerOverworldResponse
from common.gemini import Gemini, GeminiModel
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
from overworld_map.schemas import OverworldMap
from raw_memory.schemas import RawMemory, RawMemoryPiece


class DecisionMakerOverworldService:
    """A service that makes decisions based on the current game state in the overworld."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        raw_memory: RawMemory,
        current_map: OverworldMap,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = Gemini(GeminiModel.FLASH)
        self.raw_memory = raw_memory
        self.current_map = current_map

    async def make_decision(self) -> Button:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        img = await self.emulator.get_screenshot()
        prompt = DECISION_MAKER_OVERWORLD_PROMPT.format(
            raw_memory=self.raw_memory,
            current_map=self.current_map,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=DecisionMakerOverworldResponse,
        )
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                timestamp=datetime.now(),
                content=str(response),
            )
        )
        await self.emulator.press_buttons([response.button])
        return response.button
