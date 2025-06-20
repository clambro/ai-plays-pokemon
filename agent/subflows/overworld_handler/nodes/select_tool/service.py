from loguru import logger

from agent.subflows.overworld_handler.enums import OverworldTool
from agent.subflows.overworld_handler.nodes.select_tool.prompts import (
    BUTTON_TOOL_INFO,
    CRITIQUE_TOOL_INFO,
    NAVIGATION_TOOL_INFO,
    SELECT_TOOL_PROMPT,
)
from agent.subflows.overworld_handler.nodes.select_tool.schemas import SelectToolResponse
from common.constants import MIN_ITERATIONS_PER_CRITIQUE
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory, RawMemoryPiece
from overworld_map.schemas import OverworldMap


class SelectToolService:
    """A service that selects a tool based on the current game state in the overworld."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

    def __init__(  # noqa: PLR0913
        self,
        iteration: int,
        raw_memory: RawMemory,
        current_map: OverworldMap,
        last_critique_iteration: int,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.current_map = current_map
        self.last_critique_iteration = last_critique_iteration
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def select_tool(self) -> tuple[OverworldTool, RawMemory]:
        """Select a tool based on the current overworld game state."""
        game_state = self.emulator.get_game_state()
        img = self.emulator.get_screenshot()
        prompt = SELECT_TOOL_PROMPT.format(
            state=self.state_string_builder(game_state),
            tools=self._get_available_tool_info(),
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=SelectToolResponse,
                prompt_name="select_overworld_tool",
            )
            tool = OverworldTool(response.tool)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error selecting tool. Defaulting to pressing buttons. {e}")
            return OverworldTool.PRESS_BUTTONS, self.raw_memory

        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=(
                    f"Current map: {game_state.map.id.name} at coordinates"
                    f" {game_state.player.coords}, facing {game_state.player.direction.name}."
                    f" {response.thoughts}"
                ),
            ),
        )
        return tool, self.raw_memory

    def _get_available_tool_info(self) -> str:
        """Get the information about the available tools."""
        info = [BUTTON_TOOL_INFO, NAVIGATION_TOOL_INFO]  # These two are always available.

        if self.iteration - self.last_critique_iteration >= MIN_ITERATIONS_PER_CRITIQUE:
            info.append(CRITIQUE_TOOL_INFO)

        return "\n".join(info)
