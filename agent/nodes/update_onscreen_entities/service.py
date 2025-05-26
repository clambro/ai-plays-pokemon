import asyncio
from typing import TypeVar

from loguru import logger
from PIL.Image import Image

from agent.nodes.update_onscreen_entities.prompts import (
    UPDATE_SIGNS_PROMPT,
    UPDATE_SPRITES_PROMPT,
    UPDATE_WARPS_PROMPT,
)
from agent.nodes.update_onscreen_entities.schemas import UpdateEntitiesResponse
from common.llm_service import GeminiLLMEnum, GeminiLLMService
from database.sign_memory.repository import update_sign_memory
from database.sign_memory.schemas import SignMemoryUpdate
from database.sprite_memory.repository import update_sprite_memory
from database.sprite_memory.schemas import SpriteMemoryUpdate
from database.warp_memory.repository import update_warp_memory
from database.warp_memory.schemas import WarpMemoryUpdate
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from long_term_memory.schemas import LongTermMemory
from overworld_map.schemas import OverworldMap, OverworldSign, OverworldSprite, OverworldWarp
from raw_memory.schemas import RawMemory
from summary_memory.schemas import SummaryMemory

OverworldEntity = TypeVar("OverworldEntity", OverworldSprite, OverworldWarp, OverworldSign)


class UpdateOnscreenEntitiesService:
    """Service for updating the current map."""

    def __init__(
        self,
        emulator: YellowLegacyEmulator,
        iteration: int,
        raw_memory: RawMemory,
        current_map: OverworldMap,
        summary_memory: SummaryMemory,
        long_term_memory: LongTermMemory,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.raw_memory = raw_memory
        self.current_map = current_map
        self.summary_memory = summary_memory
        self.long_term_memory = long_term_memory
        self.llm_service = GeminiLLMService(GeminiLLMEnum.FLASH)

    async def update_onscreen_entities(self) -> None:
        """
        Update the long-term memory of the valid targets for updating, as defined in
        _get_updatable_entities.
        """
        game_state = await self.emulator.get_game_state()
        screenshot = await self.emulator.get_screenshot()
        tasks = []
        updatable_sprites = self._get_updatable_entities(
            list(self.current_map.known_sprites.values()),
            game_state,
        )
        if updatable_sprites:
            tasks.append(self._update_sprites(updatable_sprites, screenshot, game_state))

        updatable_warps = self._get_updatable_entities(
            list(self.current_map.known_warps.values()),
            game_state,
        )
        if updatable_warps:
            tasks.append(self._update_warps(updatable_warps, screenshot, game_state))

        updatable_signs = self._get_updatable_entities(
            list(self.current_map.known_signs.values()),
            game_state,
        )
        if updatable_signs:
            tasks.append(self._update_signs(updatable_signs, screenshot, game_state))

        await asyncio.gather(*tasks)

    @staticmethod
    def _get_updatable_entities(
        known_entities: list[OverworldEntity],
        game_state: YellowLegacyGameState,
    ) -> list[OverworldEntity]:
        """
        Get the entities that are valid targets for updating, meaning they are either within two
        blocks of the player, or they have no description in the long-term memory.
        """
        updatable_entities: list[OverworldEntity] = []
        for entity in known_entities:
            if (
                entity.description is None
                or abs(entity.y - game_state.player.y) + abs(entity.x - game_state.player.x) <= 2
            ):
                updatable_entities.append(entity)
        return updatable_entities

    async def _update_sprites(
        self,
        sprites: list[OverworldSprite],
        screenshot: Image,
        game_state: YellowLegacyGameState,
    ) -> None:
        """Update the long-term memory of the sprites."""
        m_id = self.current_map.id
        sprite_text = "\n".join([f"- [{s.index}] {s.to_string(m_id)}" for s in sprites])
        prompt = UPDATE_SPRITES_PROMPT.format(
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            long_term_memory=self.long_term_memory,
            map_info=self.current_map.to_string(game_state),
            player_info=game_state.player_info,
            sprites=sprite_text.strip(),
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[screenshot, prompt],
                schema=UpdateEntitiesResponse,
            )
            asyncio.gather(
                *[
                    update_sprite_memory(
                        SpriteMemoryUpdate(
                            map_id=self.current_map.id,
                            sprite_id=u.index,
                            description=u.description,
                            iteration=self.iteration,
                        ),
                    )
                    for u in response.updates
                ],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error updating sprites. Skipping. {e}")
            return

    async def _update_warps(
        self,
        warps: list[OverworldWarp],
        screenshot: Image,
        game_state: YellowLegacyGameState,
    ) -> None:
        """Update the long-term memory of the sprites."""
        m_id = self.current_map.id
        warp_text = "\n".join([f"- [{w.index}] {w.to_string(m_id)}" for w in warps])
        prompt = UPDATE_WARPS_PROMPT.format(
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            long_term_memory=self.long_term_memory,
            map_info=self.current_map.to_string(game_state),
            player_info=game_state.player_info,
            warps=warp_text.strip(),
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[screenshot, prompt],
                schema=UpdateEntitiesResponse,
            )
            asyncio.gather(
                *[
                    update_warp_memory(
                        WarpMemoryUpdate(
                            map_id=self.current_map.id,
                            warp_id=u.index,
                            description=u.description,
                            iteration=self.iteration,
                        ),
                    )
                    for u in response.updates
                ],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error updating warps. Skipping. {e}")
            return

    async def _update_signs(
        self,
        signs: list[OverworldSign],
        screenshot: Image,
        game_state: YellowLegacyGameState,
    ) -> None:
        """Update the long-term memory of the signs."""
        m_id = self.current_map.id
        sign_text = "\n".join([f"- [{s.index}] {s.to_string(m_id)}" for s in signs])
        prompt = UPDATE_SIGNS_PROMPT.format(
            raw_memory=self.raw_memory,
            summary_memory=self.summary_memory,
            long_term_memory=self.long_term_memory,
            map_info=self.current_map.to_string(game_state),
            player_info=game_state.player_info,
            signs=sign_text.strip(),
        )
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[screenshot, prompt],
                schema=UpdateEntitiesResponse,
            )
            asyncio.gather(
                *[
                    update_sign_memory(
                        SignMemoryUpdate(
                            map_id=self.current_map.id,
                            sign_id=u.index,
                            description=u.description,
                            iteration=self.iteration,
                        ),
                    )
                    for u in response.updates
                ],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error updating signs. Skipping. {e}")
            return
