"""Pydantic AI interface for using an overworld item."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.subflows.overworld_handler.tools.use_item.service import UseItemService

if TYPE_CHECKING:
    from agent.subflows.overworld_handler.context import OverworldContext


def build_use_item_tool(context: OverworldContext) -> Tool[OverworldContext]:
    """Build the item-use tool bound to the current overworld context."""

    async def use_item(
        inventory_slot: Annotated[int, Field(ge=0)],
    ) -> str:
        """Use an item from the current inventory.

        The use item tool allows you to use an item from your inventory in the
        overworld. It is useful for:

        - Using helpful items like REPEL, ESCAPE ROPE, evolution stones, etc.
        - Teaching a TM or HM to a Pokemon.
        - Using a healing item like a POTION or a REVIVE. This is still allowed
          outside of battle in hard mode.

        The item must be in your inventory for you to use it. If you don't have
        the item in your inventory, you cannot use it. The inventory slot is
        the zero-based index shown in ``inventory_indices`` in the prompt.

        If the item requires a target Pokemon (e.g. an evolution stone or a
        healing item), decide which Pokemon you want to use it on. The
        resulting target-selection screen will be handled on the next
        iteration.

        Args:
            inventory_slot: Zero-based inventory slot of the item to use.

        Returns:
            Confirmation or failure details for the attempted item use.
        """
        service = UseItemService(
            rolling_memory=context.state.rolling_memory,
            emulator=context.emulator,
        )
        await service.use_item(inventory_slot)
        return f"Attempted to use inventory slot {inventory_slot}."

    return Tool(use_item, require_parameter_descriptions=True)
