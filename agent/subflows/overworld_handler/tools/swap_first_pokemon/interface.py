"""Pydantic AI interface for changing the lead Pokemon."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.subflows.overworld_handler.tools.swap_first_pokemon.service import (
    SwapFirstPokemonService,
)
from agent.subflows.overworld_handler.utils import (
    OverworldToolResult,
    complete_overworld_action,
)

if TYPE_CHECKING:
    from agent.subflows.overworld_handler.context import OverworldContext


def build_swap_first_pokemon_tool(
    context: OverworldContext,
) -> Tool[OverworldContext]:
    """Build the party-reordering tool bound to the current overworld context."""

    async def swap_first_pokemon(
        party_slot: Annotated[int, Field(ge=1, le=5)],
    ) -> OverworldToolResult:
        """Put another party Pokemon in the first position.

        This will make that Pokemon your lead Pokemon in battle (assuming it
        has not fainted).

        This tool is useful for:

        - Leading with an advantageous Pokemon before a major battle.
        - Training a specific Pokemon by having it come out first in battle. If
          you want to train a specific Pokemon, use this tool to put it in the
          first position before starting your training session.
        - Keeping your party members at roughly the same level as one-another
          by changing which Pokemon is the first to see action in battle.

        Remember that Pokemon only gain experience when they are used in
        battle. Putting a Pokemon in the first position is a good way to
        guarantee that it will gain experience (assuming it has not fainted and
        is not at the level cap).

        The current party order is shown in the ``player_info`` section of the
        prompt. If you are happy with the order of your party, don't use this
        tool.

        Args:
            party_slot: Zero-based non-lead party slot of the Pokemon that should become the lead.

        Returns:
            Fresh overworld context after changing the party order.
        """
        service = SwapFirstPokemonService(
            rolling_memory=context.state.rolling_memory,
            emulator=context.emulator,
        )
        result = await service.swap_first_pokemon(party_slot)
        return await complete_overworld_action(context, result)

    return Tool(swap_first_pokemon, require_parameter_descriptions=True)
