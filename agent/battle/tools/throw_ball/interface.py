"""Pydantic AI interface for throwing a Poke Ball."""

from typing import TYPE_CHECKING

from pydantic_ai import Tool

from agent.battle.tools.errors import BattleActionUnavailableError
from agent.battle.tools.throw_ball.service import (
    throw_ball as throw_ball_service,
)
from agent.battle.tools.utils import (
    BattleToolResult,
    complete_battle_action,
    refresh_battle_observation,
)
from common.enums import PokeballItem

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_throw_ball_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the throw-ball tool bound to the current battle context."""

    async def throw_ball(
        ball_type: PokeballItem,
    ) -> BattleToolResult:
        """Throw an available Poke Ball during a wild battle.

        The selected ball must be present in the player's current inventory.

        Args:
            ball_type: Type of Poke Ball to throw.

        Returns:
            Fresh battle context after the attempted throw.
        """
        try:
            result = await throw_ball_service(
                emulator=context.emulator,
                ball_type=PokeballItem(ball_type),
            )
        except BattleActionUnavailableError as error:
            return await refresh_battle_observation(
                context,
                action_result=str(error),
            )
        return await complete_battle_action(context, result)

    return Tool(throw_ball, require_parameter_descriptions=True)
