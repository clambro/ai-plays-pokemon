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
from database.map_entity_memory.repository import apply_map_entity_changes
from database.map_entity_memory.schemas import MapEntityMemoryUpdate
from llm.service import OpenAILLMService
from overworld_map.service import update_map_with_screen_info

if TYPE_CHECKING:
    from PIL.Image import Image

    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from overworld_map.schemas import OverworldMap, OverworldSign, OverworldSprite

llm_service = OpenAILLMService()


async def update_map(
    *,
    iteration: int,
    current_map: OverworldMap,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> OverworldMap:
    """Update explored terrain and nearby entity descriptions.

    Args:
        iteration: Current agent iteration used to timestamp map-memory updates.
        current_map: Explored map to update from the visible screen.
        state_string_builder: Formatter for the current overworld state and map context.
        emulator: Running emulator used to inspect the state and capture its screen.

    Returns:
        The updated explored map.
    """
    game_state, screenshot = await emulator.get_game_state_with_screenshot()
    current_map = await update_map_with_screen_info(iteration, game_state, current_map)
    update_groups = await asyncio.gather(
        _get_entity_updates(
            list(current_map.known_sprites.values()),
            MapEntityType.SPRITE,
            screenshot,
            game_state,
            UPDATE_SPRITES_PROMPT,
            iteration=iteration,
            current_map=current_map,
            state_string_builder=state_string_builder,
        ),
        _get_entity_updates(
            list(current_map.known_signs.values()),
            MapEntityType.SIGN,
            screenshot,
            game_state,
            UPDATE_SIGNS_PROMPT,
            iteration=iteration,
            current_map=current_map,
            state_string_builder=state_string_builder,
        ),
    )
    updates = [update for group in update_groups for update in group]
    await apply_map_entity_changes(updates=updates)

    return current_map


async def _get_entity_updates(  # noqa: PLR0913
    entities: list[OverworldSprite | OverworldSign],
    entity_type: MapEntityType,
    screenshot: Image,
    game_state: YellowLegacyGameState,
    prompt: str,
    *,
    iteration: int,
    current_map: OverworldMap,
    state_string_builder: StateStringBuilder,
) -> list[MapEntityMemoryUpdate]:
    """Describe nearby entities of one type.

    Entities farther than two tiles from the player are excluded to reduce hallucinations.

    Args:
        entities: Known sprites or signs that may need descriptions.
        entity_type: Entity category used for telemetry and persistence.
        screenshot: Current game screen supplied to the model.
        game_state: Current parsed emulator state.
        prompt: Prompt template for the entity category.
        iteration: Current agent iteration used to timestamp updates.
        current_map: Explored map owning the entities.
        state_string_builder: Formatter for the current game state.
    """
    max_distance = 2
    updatable_entities = [
        e for e in entities if (e.coords - game_state.player.coords).length <= max_distance
    ]
    if not updatable_entities:
        return []

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
        )
        return [
            MapEntityMemoryUpdate(
                map_id=current_map.id,
                entity_id=update.index,
                entity_type=entity_type,
                description=update.description,
                iteration=iteration,
            )
            for update in response.updates
        ]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error updating entities. Skipping. {e}")
        return []
