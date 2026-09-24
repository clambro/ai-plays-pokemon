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
        """Switch the active Pokemon to a selected party member.

        Select the party member by its zero-based slot. This also selects a
        replacement after the active Pokemon faints. Fainted Pokemon cannot
        be selected. Note that switching Pokemon consumes your turn, leaving
        the incoming Pokemon open to attack. Carelessly switching Pokemon is
        thus the fastest way to lose a battle.

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
