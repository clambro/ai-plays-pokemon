"""Pydantic AI interface for throwing a Poke Ball."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import ModelRetry, Tool

from agent.subflows.battle_handler.tools.errors import BattleActionUnavailableError
from agent.subflows.battle_handler.tools.throw_ball.service import (
    throw_ball as throw_ball_service,
)
from common.enums import PokeballItem

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext


def build_throw_ball_tool(context: BattleContext) -> Tool[BattleContext]:
    """Build the throw-ball tool bound to the current battle context."""

    async def throw_ball(
        reason: Annotated[str, Field(min_length=1)],
        ball_type: PokeballItem,
    ) -> str:
        """Throw an available Poke Ball during a wild battle.

        The selected ball must be present in the player's current inventory.

        Args:
            reason: Brief first-person explanation of why this ball should be thrown.
            ball_type: Type of Poke Ball to throw.

        Returns:
            Confirmation of the attempted throw.

        Raises:
            ModelRetry: The requested ball is unavailable in the latest game state.
        """
        try:
            return await throw_ball_service(
                rolling_memory=context.rolling_memory,
                emulator=context.emulator,
                reason=reason,
                ball_type=PokeballItem(ball_type),
            )
        except BattleActionUnavailableError as error:
            raise ModelRetry(str(error)) from error

    return Tool(throw_ball, require_parameter_descriptions=True)
