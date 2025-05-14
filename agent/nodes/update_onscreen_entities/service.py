import asyncio

from loguru import logger
from PIL.Image import Image

from agent.nodes.update_onscreen_entities.prompts import UPDATE_SPRITES_PROMPT, UPDATE_WARPS_PROMPT
from agent.nodes.update_onscreen_entities.schemas import UpdateEntitiesResponse
from common.gemini import Gemini, GeminiModel
from database.sprite_memory.repository import update_sprite_memory
from database.sprite_memory.schemas import SpriteMemory
from database.warp_memory.repository import update_warp_memory
from database.warp_memory.schemas import WarpMemory
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from emulator.schemas import Sprite, Warp
from overworld_map.schemas import OverworldMap
from raw_memory.schemas import RawMemory


class UpdateOnscreenEntitiesService:
    """Service for updating the current map."""

    def __init__(
        self,
        emulator: YellowLegacyEmulator,
        raw_memory: RawMemory,
        current_map: OverworldMap,
    ) -> None:
        self.emulator = emulator
        self.raw_memory = raw_memory
        self.current_map = current_map
        self.llm_service = Gemini(GeminiModel.FLASH)

    async def update_onscreen_entities(self) -> None:
        """Update the long-term memory of the onscreen entities."""
        game_state = await self.emulator.get_game_state()
        _, sprites, warps = game_state.get_ascii_screen()
        screenshot = await self.emulator.get_screenshot()
        if sprites:
            await self._update_sprites(sprites, screenshot, game_state)
        if warps:
            await self._update_warps(warps, screenshot, game_state)

    async def _update_sprites(
        self,
        sprites: list[Sprite],
        screenshot: Image,
        game_state: YellowLegacyGameState,
    ) -> None:
        """Update the long-term memory of the sprites."""
        sprite_text = "\n".join([f"- [{i}] {s}" for i, s in enumerate(sprites)])
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
                        SpriteMemory(
                            map_id=self.current_map.id,
                            sprite_id=u.index,
                            description=u.description,
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
        warps: list[Warp],
        screenshot: Image,
        game_state: YellowLegacyGameState,
    ) -> None:
        """Update the long-term memory of the sprites."""
        warp_text = "\n".join([f"- [{i}] {w}" for i, w in enumerate(warps)])
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
                        WarpMemory(
                            map_id=self.current_map.id,
                            warp_id=u.index,
                            description=u.description,
                        ),
                    )
                    for u in response.updates
                ],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error updating warps. Skipping. {e}")
            return
