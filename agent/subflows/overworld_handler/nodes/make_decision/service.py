from loguru import logger

from agent.subflows.overworld_handler.nodes.make_decision.prompts import (
    DECISION_MAKER_OVERWORLD_PROMPT,
)
from agent.subflows.overworld_handler.nodes.make_decision.schemas import (
    DecisionMakerOverworldDecision,
    DecisionMakerOverworldResponse,
)
from common.enums import AsciiTiles, Tool
from common.goals import Goals
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from emulator.emulator import YellowLegacyEmulator
from emulator.enums import Button, FacingDirection
from memory.agent_memory import AgentMemory
from memory.raw_memory import RawMemoryPiece
from overworld_map.schemas import OverworldMap


class MakeDecisionService:
    """A service that makes decisions based on the current game state in the overworld."""

    def __init__(
        self,
        iteration: int,
        emulator: YellowLegacyEmulator,
        agent_memory: AgentMemory,
        current_map: OverworldMap,
        goals: Goals,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)
        self.agent_memory = agent_memory
        self.current_map = current_map
        self.goals = goals

    async def make_decision(self) -> DecisionMakerOverworldDecision:
        """Make a decision based on the current overworld game state."""
        game_state = self.emulator.get_game_state()
        img = self.emulator.get_screenshot()
        prompt = DECISION_MAKER_OVERWORLD_PROMPT.format(
            agent_memory=self.agent_memory,
            player_info=game_state.player_info,
            current_map=self.current_map.to_string(game_state),
            goals=self.goals,
            walkable_tiles=", ".join(f'"{t}"' for t in AsciiTiles.get_walkable_tiles()),
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[img, prompt],
                schema=DecisionMakerOverworldResponse,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error making decision. Skipping. {e}")
            return DecisionMakerOverworldDecision(
                agent_memory=self.agent_memory,
                tool=None,
                navigation_args=None,
            )

        map_str = game_state.cur_map.id.name
        position = (game_state.player.y, game_state.player.x)
        thought = f"Current map: {map_str} at coordinates {position}. {response.thoughts}"

        if response.navigation_args:
            self.agent_memory.append_raw_memory(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=f"{thought} Navigating to {response.navigation_args}.",
                ),
            )
            return DecisionMakerOverworldDecision(
                agent_memory=self.agent_memory,
                tool=Tool.NAVIGATION,
                navigation_args=response.navigation_args,
            )
        if response.button:
            prev_map = game_state.cur_map.id.name
            prev_coords = (game_state.player.y, game_state.player.x)
            prev_direction = game_state.player.direction
            await self.emulator.press_buttons([response.button])
            self.agent_memory.append_raw_memory(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=f"{thought} Pressed the '{response.button}' button.",
                ),
            )
            await self._check_for_collision(response.button, prev_map, prev_coords, prev_direction)
            await self._check_for_action(response.button)

        return DecisionMakerOverworldDecision(
            agent_memory=self.agent_memory,
            tool=None,
            navigation_args=None,
        )

    async def _check_for_collision(
        self,
        button: Button,
        prev_map: str,
        prev_coords: tuple[int, int],
        prev_direction: FacingDirection,
    ) -> None:
        """Check if the player bumped into a wall and add a note to the raw memory if so."""
        if button not in [Button.LEFT, Button.RIGHT, Button.UP, Button.DOWN]:
            return

        await self.emulator.wait_for_animation_to_finish()
        game_state = self.emulator.get_game_state()
        current_map = game_state.cur_map.id.name
        current_coords = (game_state.player.y, game_state.player.x)
        current_direction = game_state.player.direction
        if (
            current_map == prev_map
            and current_coords == prev_coords
            and current_direction == prev_direction
        ):
            self.agent_memory.append_raw_memory(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        f"My position did not change after pressing the '{button}' button. Did I"
                        f" bump into something?"
                    ),
                ),
            )

    async def _check_for_action(self, button: Button) -> None:
        """Check if the player hit the action button but nothing happened."""
        if button != Button.A:
            return

        await self.emulator.wait_for_animation_to_finish()
        game_state = self.emulator.get_game_state()
        if not game_state.is_text_on_screen():
            self.agent_memory.append_raw_memory(
                RawMemoryPiece(
                    iteration=self.iteration,
                    content=(
                        "I pressed the action button but nothing happened. There must not be"
                        " anything to interact with in the direction I am facing."
                    ),
                ),
            )
