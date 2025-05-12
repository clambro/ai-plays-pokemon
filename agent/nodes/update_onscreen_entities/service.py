from pathlib import Path

from loguru import logger

from agent.nodes.update_onscreen_entities.prompts import (
    UPDATE_SPRITES_PROMPT,
    UPDATE_WARPS_PROMPT,
)
from agent.nodes.update_onscreen_entities.schemas import UpdateEntitiesResponse
from common.gemini import Gemini, GeminiModel
from emulator.emulator import YellowLegacyEmulator
from PIL.Image import Image

from common.constants import SPRITE_SUBFOLDER, WARP_SUBFOLDER
from emulator.game_state import YellowLegacyGameState
from emulator.schemas import Sprite, Warp
from overworld_map.schemas import OverworldMap
from raw_memory.schemas import RawMemory


class UpdateOnscreenEntitiesService:
    """Service for updating the current map."""

    def __init__(
        self,
        emulator: YellowLegacyEmulator,
        parent_folder: Path,
        raw_memory: RawMemory,
        current_map: OverworldMap,
    ) -> None:
        self.emulator = emulator
        self.parent_folder = parent_folder
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
        sprite_text = ""
        for i, s in enumerate(sprites):
            map_id = self.current_map.id
            description = await s.to_string(self.parent_folder / SPRITE_SUBFOLDER, map_id)
            sprite_text += f"- [{i}] {description}\n"
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
            for u in response.updates:
                await sprites[u.index].save_description(
                    self.parent_folder / SPRITE_SUBFOLDER, map_id, u.description
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
        warp_text = ""
        for i, w in enumerate(warps):
            map_id = self.current_map.id
            description = await w.to_string(self.parent_folder / WARP_SUBFOLDER, map_id)
            warp_text += f"- [{i}] {description}\n"
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
            for u in response.updates:
                await warps[u.index].save_description(
                    self.parent_folder / WARP_SUBFOLDER, map_id, u.description
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error updating warps. Skipping. {e}")
            return
