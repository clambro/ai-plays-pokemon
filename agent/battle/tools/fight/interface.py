"""Pydantic AI interface for selecting a battle move."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.battle.tools.errors import BattleActionUnavailableError
from agent.battle.tools.fight.service import fight as fight_service
from agent.battle.tools.utils import (
    BattleToolResult,
    complete_battle_action,
    refresh_battle_observation,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_fight_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the fight tool bound to the current battle context."""

    async def fight(move_slot: Annotated[int, Field(ge=0, le=3)]) -> BattleToolResult:
        """Use an available move against the opposing Pokemon.

        The move slot is its zero-based position in the active Pokemon's move
        list. A move with no PP cannot be used. If every move has no PP, use
        slot 0 to make the Pokemon use STRUGGLE.

        Args:
            move_slot: Zero-based slot of the move to use.

        Returns:
            Fresh battle context after the attempted move.
        """
        try:
            result = await fight_service(
                emulator=context.emulator,
                move_slot=move_slot,
            )
        except BattleActionUnavailableError as error:
            return await refresh_battle_observation(
                context,
                action_result=str(error),
            )
        return await complete_battle_action(context, result)

    return Tool(fight, require_parameter_descriptions=True)
