"""Pydantic AI interface for switching the active Pokemon."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import ModelRetry, Tool

from agent.subflows.battle_handler.tools.errors import BattleActionUnavailableError
from agent.subflows.battle_handler.tools.switch_pokemon.service import (
    switch_pokemon as switch_pokemon_service,
)
from agent.subflows.battle_handler.utils import (
    BattleToolResult,
    complete_battle_action,
    refresh_battle_observation,
)

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext


def build_switch_pokemon_tool(context: BattleContext) -> Tool[BattleContext]:
    """Build the switch tool bound to the current battle context."""

    async def switch_pokemon(
        party_slot: Annotated[int, Field(ge=0, le=5)],
    ) -> BattleToolResult:
        """Switch to an available Pokemon in the player's party.

        The party slot is its zero-based position in the player's party. The
        active Pokemon and fainted Pokemon cannot be switched in. Switching
        consumes the turn, so the opponent can attack the Pokemon switched in.

        Args:
            party_slot: Zero-based party slot of the Pokemon to switch in.

        Returns:
            Fresh battle context after the attempted switch.

        Raises:
            ModelRetry: The requested party member is unavailable in the latest game state.
        """
        try:
            result = await switch_pokemon_service(
                rolling_memory=context.state.rolling_memory,
                emulator=context.emulator,
                party_slot=party_slot,
            )
        except BattleActionUnavailableError as error:
            retry_context = await refresh_battle_observation(
                context,
                action_result=str(error),
            )
            raise ModelRetry(retry_context) from error
        return await complete_battle_action(context, result)

    return Tool(switch_pokemon, require_parameter_descriptions=True)
