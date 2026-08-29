"""Pydantic AI interface for changing the lead Pokemon."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.overworld.tools.swap_first_pokemon.service import (
    SwapFirstPokemonService,
)
from agent.overworld.tools.utils import (
    OverworldToolResult,
    complete_overworld_action,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_swap_first_pokemon_tool(
    context: AgentContext,
) -> Tool[AgentContext]:
    """Build the party-reordering tool bound to the current overworld context."""

    async def swap_first_pokemon(
        party_slot: Annotated[int, Field(ge=1, le=5)],
    ) -> OverworldToolResult:
        """Put another party Pokemon in the first position.

        This makes that Pokemon the lead in future battles, assuming it has not
        fainted. Use it to prepare a favorable matchup or give a Pokemon you
        intend to develop more opportunities to gain experience. The current
        party order is shown in the ``party`` section of the prompt.

        Args:
            party_slot: Zero-based non-lead party slot of the Pokemon that should become the lead.

        Returns:
            Fresh screenshot and the actual party-change result.
        """
        service = SwapFirstPokemonService(
            rolling_memory=context.state.rolling_memory,
            emulator=context.emulator,
        )
        result = await service.swap_first_pokemon(party_slot)
        return await complete_overworld_action(context, result)

    return Tool(swap_first_pokemon, require_parameter_descriptions=True)
