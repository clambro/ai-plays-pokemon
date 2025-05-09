from pathlib import Path

from loguru import logger

from agent.actions.update_onscreen_entities.prompts import (
    UPDATE_SPRITES_PROMPT,
    UPDATE_WARPS_PROMPT,
)
from agent.actions.update_onscreen_entities.schemas import UpdateEntitiesResponse
from common.gemini import Gemini, GeminiModel
from emulator.emulator import YellowLegacyEmulator
from PIL.Image import Image

from emulator.enums import MapLocation
from emulator.schemas import Sprite, Warp


class UpdateOnscreenEntitiesService:
    """Service for updating the current map."""

    def __init__(self, emulator: YellowLegacyEmulator, parent_folder: Path) -> None:
        self.emulator = emulator
        self.parent_folder = parent_folder
        self.llm_service = Gemini(GeminiModel.FLASH)

    async def update_onscreen_entities(self) -> None:
        """Update the long-term memory of the onscreen entities."""
        game_state = await self.emulator.get_game_state()
        _, sprites, warps = game_state.get_ascii_screen()
        screenshot = await self.emulator.get_screenshot()
        if sprites:
            await self._update_sprites(sprites, screenshot, game_state.cur_map.id)
        if warps:
            await self._update_warps(warps, screenshot, game_state.cur_map.id)

    async def _update_sprites(
        self,
        sprites: list[Sprite],
        screenshot: Image,
        map_id: MapLocation,
    ) -> None:
        """Update the long-term memory of the sprites."""
        sprite_text = ""
        for i, s in enumerate(sprites):
            description = await s.get_description(self.parent_folder, map_id)
            sprite_text += (
                f"- [{i}] sprite_{map_id.value}_{s.index} at ({s.y}, {s.x}) - {description}\n"
            )
        prompt = UPDATE_SPRITES_PROMPT.format(sprites=sprite_text)
        print(prompt)
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[screenshot, prompt],
                schema=UpdateEntitiesResponse,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error updating sprites. Skipping. {e}")
            return
        for u in response.updates:
            await sprites[u.index].save_description(self.parent_folder, map_id, u.description)

    async def _update_warps(
        self,
        warps: list[Warp],
        screenshot: Image,
        map_id: MapLocation,
    ) -> None:
        """Update the long-term memory of the sprites."""
        warp_text = ""
        for i, w in enumerate(warps):
            description = await w.get_description(self.parent_folder, map_id)
            warp_text += (
                f"- [{i}] warp_{map_id.value}_{w.index} at ({w.y}, {w.x}) - {description}\n"
            )
        prompt = UPDATE_WARPS_PROMPT.format(warps=warp_text)
        print(prompt)
        try:
            response = await self.llm_service.get_llm_response_pydantic(
                messages=[screenshot, prompt],
                schema=UpdateEntitiesResponse,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error updating warps. Skipping. {e}")
            return
        for u in response.updates:
            await warps[u.index].save_description(self.parent_folder, map_id, u.description)
