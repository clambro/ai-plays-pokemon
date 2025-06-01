import asyncio

from loguru import logger
from PIL.Image import Image

from agent.subflows.overworld_handler.nodes.update_onscreen_entities.prompts import (
    UPDATE_SIGNS_PROMPT,
    UPDATE_SPRITES_PROMPT,
    UPDATE_WARPS_PROMPT,
)
from agent.subflows.overworld_handler.nodes.update_onscreen_entities.schemas import (
    UpdateEntitiesResponse,
)
from common.enums import MapEntityType
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from database.map_entity_memory.repository import update_map_entity_memory
from database.map_entity_memory.schemas import MapEntityMemoryUpdate
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from memory.agent_memory import AgentMemory
from overworld_map.schemas import OverworldMap, OverworldSign, OverworldSprite, OverworldWarp


class UpdateOnscreenEntitiesService:
    """Service for updating the current map."""

    def __init__(
        self,
        emulator: YellowLegacyEmulator,
        iteration: int,
        agent_memory: AgentMemory,
        current_map: OverworldMap,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.agent_memory = agent_memory
        self.current_map = current_map
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

    async def update_onscreen_entities(self) -> None:
        """
        Update the map entity memory of the valid targets for updating, as defined in
        _update_entities.
        """
        game_state = self.emulator.get_game_state()
        screenshot = self.emulator.get_screenshot()
        await asyncio.gather(
            *[
                self._update_entities(
                    list(self.current_map.known_sprites.values()),
                    MapEntityType.SPRITE,
                    screenshot,
                    game_state,
                    UPDATE_SPRITES_PROMPT,
                ),
                self._update_entities(
                    list(self.current_map.known_warps.values()),
                    MapEntityType.WARP,
                    screenshot,
                    game_state,
                    UPDATE_WARPS_PROMPT,
                ),
                self._update_entities(
                    list(self.current_map.known_signs.values()),
                    MapEntityType.SIGN,
                    screenshot,
                    game_state,
                    UPDATE_SIGNS_PROMPT,
                ),
            ],
        )

    async def _update_entities(
        self,
        entities: list[OverworldSprite | OverworldWarp | OverworldSign],
        entity_type: MapEntityType,
        screenshot: Image,
        game_state: YellowLegacyGameState,
        prompt: str,
    ) -> None:
        """
        Update the map memory of the entities of the given type, as long as they either have no
        description in the map entity memory, or they are within two blocks of the player.

        :param entities: The entities to update.
        :param entity_type: The type of entity to update.
        :param screenshot: The screenshot of the current screen.
        :param game_state: The current game state.
        :param prompt: The prompt to use for the LLM.
        """
        updatable_entities: list[OverworldSprite | OverworldWarp | OverworldSign] = []
        for e in entities:
            if (
                e.description is None
                or abs(e.y - game_state.player.y) + abs(e.x - game_state.player.x) <= 2
            ):
                updatable_entities.append(e)
        if not updatable_entities:
            return

        m_id = self.current_map.id
        entity_text = "\n".join([f"- [{e.index}] {e.to_string(m_id)}" for e in updatable_entities])
        prompt = prompt.format(
            agent_memory=self.agent_memory,
            map_info=self.current_map.to_string(game_state),
            player_info=game_state.player_info,
            entities=entity_text.strip(),
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[screenshot, prompt],
                schema=UpdateEntitiesResponse,
            )
            await asyncio.gather(
                *[
                    update_map_entity_memory(
                        MapEntityMemoryUpdate(
                            map_id=self.current_map.id,
                            entity_id=u.index,
                            entity_type=entity_type,
                            description=u.description,
                            iteration=self.iteration,
                        ),
                    )
                    for u in response.updates
                ],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error updating entities. Skipping. {e}")
