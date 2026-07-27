"""Business logic for update map in the overworld subflow."""

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from agent.subflows.overworld_handler.nodes.update_map.prompts import (
    UPDATE_SIGNS_PROMPT,
    UPDATE_SPRITES_PROMPT,
)
from agent.subflows.overworld_handler.nodes.update_map.schemas import UpdateEntitiesResponse
from common.enums import MapEntityType
from database.map_entity_memory.repository import update_map_entity_memory
from database.map_entity_memory.schemas import MapEntityMemoryUpdate
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService
from overworld_map.service import update_map_with_screen_info

if TYPE_CHECKING:
    from PIL.Image import Image

    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from overworld_map.schemas import OverworldMap, OverworldSign, OverworldSprite

llm_service = GeminiLLMService(GEMINI_FLASH_2_5)


async def update_map(
    *,
    iteration: int,
    current_map: OverworldMap,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> OverworldMap:
    """Update the current map and nearby entities with the latest screen info."""
    screenshot = emulator.get_screenshot()
    game_state = emulator.get_game_state()
    current_map = await update_map_with_screen_info(iteration, game_state, current_map)
    await asyncio.gather(
        *[
            _update_entities(
                list(current_map.known_sprites.values()),
                MapEntityType.SPRITE,
                screenshot,
                game_state,
                UPDATE_SPRITES_PROMPT,
                iteration=iteration,
                current_map=current_map,
                state_string_builder=state_string_builder,
            ),
            _update_entities(
                list(current_map.known_signs.values()),
                MapEntityType.SIGN,
                screenshot,
                game_state,
                UPDATE_SIGNS_PROMPT,
                iteration=iteration,
                current_map=current_map,
                state_string_builder=state_string_builder,
            ),
        ],
    )
    return current_map


async def _update_entities(  # noqa: PLR0913
    entities: list[OverworldSprite | OverworldSign],
    entity_type: MapEntityType,
    screenshot: Image,
    game_state: YellowLegacyGameState,
    prompt: str,
    *,
    iteration: int,
    current_map: OverworldMap,
    state_string_builder: StateStringBuilder,
) -> None:
    """
    Update the map memory of the entities of the given type, as long as they are within a
    certain distance of the player. Updating entities that are too far away introduces
    hallucinations.

    :param entities: The entities to update.
    :param entity_type: The type of entity to update.
    :param screenshot: The screenshot of the current screen.
    :param game_state: The current game state.
    :param prompt: The prompt to use for the LLM.
    """
    max_distance = 2
    updatable_entities = [
        e for e in entities if (e.coords - game_state.player.coords).length <= max_distance
    ]
    if not updatable_entities:
        return

    entity_text = "\n".join(
        [f"- [{e.index}] {e.to_string(current_map.id)}" for e in updatable_entities],
    )
    prompt = prompt.format(
        state=state_string_builder(game_state),
        entities=entity_text.strip(),
    )
    try:
        response = await llm_service.get_llm_response_pydantic(
            messages=[screenshot, prompt],
            schema=UpdateEntitiesResponse,
            prompt_name=f"update_{entity_type.name.lower()}s",
        )
        await asyncio.gather(
            *[
                update_map_entity_memory(
                    MapEntityMemoryUpdate(
                        map_id=current_map.id,
                        entity_id=u.index,
                        entity_type=entity_type,
                        description=u.description,
                        iteration=iteration,
                    ),
                )
                for u in response.updates
            ],
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error updating entities. Skipping. {e}")
