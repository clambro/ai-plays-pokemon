from datetime import datetime

from loguru import logger
from agent.actions.decision_maker_overworld.prompts import DECISION_MAKER_OVERWORLD_PROMPT
from agent.actions.decision_maker_overworld.schemas import DecisionMakerOverworldResponse
from common.enums import AgentStateHandler
from common.gemini import Gemini, GeminiModel
from common.goals import Goals
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
from emulator.game_state import YellowLegacyGameState
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
        goals: Goals,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = Gemini(GeminiModel.FLASH)
        self.raw_memory = raw_memory
        self.current_map = current_map
        self.goals = goals

    async def make_decision(self) -> AgentStateHandler | None:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        game_state = await self.emulator.get_game_state()
        img = await self.emulator.get_screenshot()
        prompt = DECISION_MAKER_OVERWORLD_PROMPT.format(
            raw_memory=self.raw_memory,
            player_info=game_state.player_info,
            current_map=await self.current_map.to_string(game_state),
            goals=self.goals,
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=DecisionMakerOverworldResponse,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")
            return None

        if response.navigation_args:
            return AgentStateHandler.OVERWORLD  # Pass control to the navigation node.
        elif response.button:
            await self._press_button(game_state, response.thoughts, response.button)
            return None

    async def _press_button(
        self,
        game_state: YellowLegacyGameState,
        thoughts: str,
        button: Button,
    ) -> None:
        """Press the given button."""
        await self.emulator.press_buttons([button])
        position = (game_state.player.y, game_state.player.x)
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                timestamp=datetime.now(),
                content=f'Current position: {position}. {thoughts} Pressed the "{button}" button.',
            )
        )
