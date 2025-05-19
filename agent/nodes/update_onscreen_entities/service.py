import asyncio

from loguru import logger
from PIL.Image import Image

from agent.nodes.update_onscreen_entities.prompts import (
    UPDATE_SIGNS_PROMPT,
    UPDATE_SPRITES_PROMPT,
    UPDATE_WARPS_PROMPT,
)
from agent.nodes.update_onscreen_entities.schemas import UpdateEntitiesResponse
from common.gemini import Gemini, GeminiModel
from database.sign_memory.repository import update_sign_memory
from database.sign_memory.schemas import SignMemoryCreateUpdate
from database.sprite_memory.repository import update_sprite_memory
from database.sprite_memory.schemas import SpriteMemoryCreateUpdate
from database.warp_memory.repository import update_warp_memory
from database.warp_memory.schemas import WarpMemoryCreateUpdate
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from overworld_map.schemas import OverworldMap, OverworldSign, OverworldSprite, OverworldWarp
from raw_memory.schemas import RawMemory


class UpdateOnscreenEntitiesService:
    """Service for updating the current map."""

    def __init__(
        self,
        emulator: YellowLegacyEmulator,
        iteration: int,
        raw_memory: RawMemory,
        current_map: OverworldMap,
    ) -> None:
        self.iteration = iteration
        self.emulator = emulator
        self.raw_memory = raw_memory
        self.current_map = current_map
        self.llm_service = Gemini(GeminiModel.FLASH)

    async def update_onscreen_entities(self) -> None:
        """Update the long-term memory of the onscreen entities."""
        game_state = await self.emulator.get_game_state()
        _, sprites, warps, signs = game_state.get_ascii_screen()
        screenshot = await self.emulator.get_screenshot()
        if sprites:
            known_sprites = self.current_map.known_sprites
            sprites = [known_sprites[s.index] for s in sprites if s.index in known_sprites]
            await self._update_sprites(sprites, screenshot, game_state)
        if warps:
            known_warps = self.current_map.known_warps
            warps = [known_warps[w.index] for w in warps if w.index in known_warps]
            await self._update_warps(warps, screenshot, game_state)
        if signs:
            known_signs = self.current_map.known_signs
            signs = [known_signs[s.index] for s in signs if s.index in known_signs]
            await self._update_signs(signs, screenshot, game_state)

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
            map_info=await self.current_map.to_string(game_state),
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
                        SpriteMemoryCreateUpdate(
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
            map_info=await self.current_map.to_string(game_state),
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
                        WarpMemoryCreateUpdate(
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
            map_info=await self.current_map.to_string(game_state),
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
                        SignMemoryCreateUpdate(
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
