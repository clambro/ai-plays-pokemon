"""Pydantic AI interface for switching the active Pokemon."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.battle.tools.errors import BattleActionUnavailableError
from agent.battle.tools.switch_pokemon.service import (
    switch_pokemon as switch_pokemon_service,
)
from agent.battle.tools.utils import (
    BattleToolResult,
    complete_battle_action,
    refresh_battle_observation,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_switch_pokemon_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the switch tool bound to the current battle context."""

    async def switch_pokemon(
        party_slot: Annotated[int, Field(ge=0, le=5)],
    ) -> BattleToolResult:
        """Choose an available Pokemon in the player's party.

        Use this from the fight menu to switch voluntarily, or from the Pokemon
        menu to choose a replacement after your active Pokemon faints. The
        party slot is its zero-based position in the player's party. Fainted
        Pokemon cannot be selected. A voluntary switch consumes the turn and
        exposes the incoming Pokemon to an attack; a replacement after a faint
        does not. Use voluntary switching sparingly, as repeated switching can
        easily cost you the battle.

        Args:
            party_slot: Zero-based party slot of the Pokemon to switch in.

        Returns:
            Fresh battle context after the attempted switch.
        """
        try:
            result = await switch_pokemon_service(emulator=context.emulator, party_slot=party_slot)
        except BattleActionUnavailableError as error:
            return await refresh_battle_observation(
                context,
                action_result=str(error),
            )
        return await complete_battle_action(context, result)

    return Tool(switch_pokemon, require_parameter_descriptions=True)
