"""Pydantic AI interface for updating nearby sprite descriptions."""

import inspect
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, Field
from pydantic_ai import Tool

from agent.subflows.overworld_handler.tools.update_sprites.service import (
    update_sprites as update_sprites_service,
)
from agent.subflows.overworld_handler.utils import (
    OverworldToolResult,
    complete_overworld_action,
)

if TYPE_CHECKING:
    from agent.subflows.overworld_handler.context import OverworldContext
    from overworld_map.schemas import OverworldSprite


class SpriteDescriptionUpdate(BaseModel):
    """A new description for one nearby sprite."""

    index: int
    description: str


def build_update_sprites_tool(
    context: OverworldContext,
    eligible_sprites: list[OverworldSprite],
) -> Tool[OverworldContext]:
    """Build the sprite-description tool for the nearby sprites."""
    current_map = context.current_map
    eligible_indices = {sprite.index for sprite in eligible_sprites}

    async def update_sprites(
        updates: Annotated[list[SpriteDescriptionUpdate], Field(min_length=1)],
    ) -> OverworldToolResult:
        """Update long-term descriptions of nearby sprites.

        Sprites are usually people or item balls, but may also be objects or
        Pokemon. Record the kind of sprite and any useful information learned
        by interacting with it, including what a person recently said.

        Do not infer a sprite's identity or purpose from the screenshot alone.
        If its identity is still unknown, say so explicitly. Do not include its
        position in the description because the game supplies that separately.
        Use this tool only when there is new information worth preserving.

        Args:
            updates: Sprite indices and their complete new descriptions.

        Returns:
            Fresh screenshot and the description-update result.
        """
        valid_updates = {
            update.index: update.description
            for update in updates
            if update.index in eligible_indices
        }
        await update_sprites_service(
            map_id=current_map.id,
            iteration=context.state.iteration,
            updates=valid_updates.items(),
        )

        updated = sorted(valid_updates)
        ignored = sorted({update.index for update in updates} - eligible_indices)
        result = f"Updated sprite descriptions for indices: {updated}."
        if ignored:
            result += f" Ignored ineligible sprite indices: {ignored}."
        context.state.rolling_memory.add_memory(result)
        return await complete_overworld_action(context, result)

    entity_text = "\n".join(
        f"- [{sprite.index}] {sprite.to_string(current_map.id)}" for sprite in eligible_sprites
    )
    description = (
        f"{inspect.cleandoc(update_sprites.__doc__ or '')}\n\n"
        f"Eligible nearby sprites:\n{entity_text}"
    )
    return Tool(
        update_sprites,
        description=description,
        require_parameter_descriptions=True,
    )
