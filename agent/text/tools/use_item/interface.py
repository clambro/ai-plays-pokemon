"""Pydantic AI interface for using items from an open bag."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent import items
from agent.text.utils import TextToolResult, complete_text_action

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_use_item_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the item-use tool bound to the current text context."""

    async def use_item(inventory_slot: Annotated[int, Field(ge=0)]) -> TextToolResult:
        """Use an item from the open bag without scrolling manually.

        Select the zero-based inventory index and choose USE. If the item needs
        a target Pokemon or another decision, handle the resulting screen next.

        Args:
            inventory_slot: Zero-based slot shown in the current inventory.

        Returns:
            Fresh text context after attempting to use the item.
        """
        previous_game_state = await context.emulator.get_game_state()
        result = await items.use_item(
            emulator=context.emulator,
            item_index=inventory_slot,
        )
        return await complete_text_action(context, result, previous_game_state=previous_game_state)

    return Tool(use_item, require_parameter_descriptions=True)
