from loguru import logger

from agent.nodes.decision_maker_overworld.prompts import DECISION_MAKER_OVERWORLD_PROMPT
from agent.nodes.decision_maker_overworld.schemas import DecisionMakerOverworldResponse
from agent.schemas import NavigationArgs
from common.enums import AsciiTiles, Tool
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button
from long_term_memory.schemas import LongTermMemory
from overworld_map.schemas import OverworldMap
from raw_memory.schemas import RawMemory, RawMemoryPiece
from summary_memory.schemas import SummaryMemory


class DecisionMakerOverworldService:
    """A service that makes decisions based on the current game state in the overworld."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        raw_memory: RawMemory,
        current_map: OverworldMap,
        goals: Goals,
        summary_memory: SummaryMemory,
        long_term_memory: LongTermMemory,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)
        self.raw_memory = raw_memory
        self.current_map = current_map
        self.goals = goals
        self.summary_memory = summary_memory
        self.long_term_memory = long_term_memory

    async def make_decision(self) -> tuple[Tool | None, NavigationArgs | None]:
        """
        Make a decision based on the current game state.

        :return: The button to press.
        """
        game_state = await self.emulator.get_game_state()
        img = await self.emulator.get_screenshot()
        prompt = DECISION_MAKER_OVERWORLD_PROMPT.format(
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            player_info=game_state.player_info,
            current_map=await self.current_map.to_string(game_state),
            goals=self.goals,
            walkable_tiles=", ".join(f'"{t}"' for t in AsciiTiles.get_walkable_tiles()),
            long_term_memory=self.long_term_memory,
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=DecisionMakerOverworldResponse,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")
            return None, None

        map_str = game_state.cur_map.id.name
        position = (game_state.player.y, game_state.player.x)
        thought = f"Current map: {map_str} at coordinates {position}. {response.thoughts}"

        if response.navigation_args:
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=f"{thought} Navigating to {response.navigation_args}.",
                ),
            )
            return Tool.NAVIGATION, response.navigation_args
        if response.button:
            prev_map = game_state.cur_map.id.name
            prev_coords = (game_state.player.y, game_state.player.x)
            await self.emulator.press_buttons([response.button])
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=f"{thought} Pressed the '{response.button}' button.",
                ),
            )
            await self._check_for_collision(response.button, prev_map, prev_coords)

        return None, None

    async def _check_for_collision(
        self,
        button: Button,
        prev_map: str,
        prev_coords: tuple[int, int],
    ) -> None:
        """Check if the player bumped into a wall and add a note to the raw memory if so."""
        if button not in [Button.LEFT, Button.RIGHT, Button.UP, Button.DOWN]:
            return

        await self.emulator.wait_for_animation_to_finish()
        game_state = await self.emulator.get_game_state()
        current_map = game_state.cur_map.id.name
        current_coords = (game_state.player.y, game_state.player.x)
        if current_map == prev_map and current_coords == prev_coords:
            self.raw_memory.append(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"My position did not change after pressing the '{button}' button. Did I"
                        f" bump into something?"
                    ),
                ),
            )
