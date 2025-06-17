from loguru import logger

from agent.subflows.overworld_handler.enums import OverworldTool
from agent.subflows.overworld_handler.nodes.select_tool.prompts import SELECT_TOOL_PROMPT
from agent.subflows.overworld_handler.nodes.select_tool.schemas import SelectToolResponse
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory, RawMemoryPiece
from overworld_map.schemas import OverworldMap


class SelectToolService:
    """A service that selects a tool based on the current game state in the overworld."""

    llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        current_map: OverworldMap,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.current_map = current_map
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def select_tool(self) -> tuple[OverworldTool, RawMemory]:
        """Select a tool based on the current overworld game state."""
        game_state = self.emulator.get_game_state()
        img = self.emulator.get_screenshot()
        prompt = SELECT_TOOL_PROMPT.format(state=self.state_string_builder(game_state))
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=SelectToolResponse,
                prompt_name="select_overworld_tool",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error selecting tool. Defaulting to pressing buttons. {e}")
            return OverworldTool.PRESS_BUTTONS, self.raw_memory

        position = (game_state.player.y, game_state.player.x)
        self.raw_memory.append(
            RawMemoryPiece(
                iteration=self.iteration,
                content=(
                    f"Current map: {game_state.map.id.name} at coordinates {position}, facing"
                    f" {game_state.player.direction.name}. {response.thoughts}"
                ),
            ),
        )
        return response.tool, self.raw_memory
