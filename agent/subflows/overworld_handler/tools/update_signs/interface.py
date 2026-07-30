"""Pydantic AI interface for updating nearby sign descriptions."""

import inspect
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, Field
from pydantic_ai import Tool

from agent.subflows.overworld_handler.tools.update_signs.service import (
    update_signs as update_signs_service,
)

if TYPE_CHECKING:
    from agent.subflows.overworld_handler.context import OverworldContext
    from overworld_map.schemas import OverworldSign


class SignDescriptionUpdate(BaseModel):
    """A new description for one nearby sign."""

    index: int
    description: str


def build_update_signs_tool(
    context: OverworldContext,
    eligible_signs: list[OverworldSign],
) -> Tool[OverworldContext]:
    """Build the sign-description tool for the nearby signs."""
    current_map = context.state.current_map
    if current_map is None:
        raise ValueError("Current map is not set")
    iteration = context.state.iteration
    if iteration is None:
        raise ValueError("Iteration is not set")

    eligible_indices = {sign.index for sign in eligible_signs}

    async def update_signs(
        updates: Annotated[list[SignDescriptionUpdate], Field(min_length=1)],
    ) -> str:
        """Update long-term descriptions of nearby signs.

        Signs are usually signposts or TVs, but may be other static places
        where informational text can be read. Record the kind of sign and any
        useful information learned by reading it.

        Do not infer what a sign says from the screenshot alone. If its meaning
        is still unknown, say so explicitly. Do not include its position in
        the description because the game supplies that separately. Use this
        tool only when there is new information worth preserving.

        Args:
            updates: Sign indices and their complete new descriptions.

        Returns:
            The sign indices whose descriptions were updated.
        """
        valid_updates = {
            update.index: update.description
            for update in updates
            if update.index in eligible_indices
        }
        await update_signs_service(
            map_id=current_map.id,
            iteration=iteration,
            updates=valid_updates.items(),
        )

        updated = sorted(valid_updates)
        ignored = sorted({update.index for update in updates} - eligible_indices)
        result = f"Updated sign descriptions for indices: {updated}."
        if ignored:
            result += f" Ignored ineligible sign indices: {ignored}."
        return result

    entity_text = "\n".join(
        f"- [{sign.index}] {sign.to_string(current_map.id)}" for sign in eligible_signs
    )
    description = (
        f"{inspect.cleandoc(update_signs.__doc__ or '')}\n\nEligible nearby signs:\n{entity_text}"
    )
    return Tool(
        update_signs,
        description=description,
        require_parameter_descriptions=True,
    )
