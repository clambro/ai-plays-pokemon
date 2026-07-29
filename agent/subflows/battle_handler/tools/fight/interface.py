"""Pydantic AI interface for selecting a battle move."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import ModelRetry, Tool

from agent.subflows.battle_handler.tools.errors import BattleActionUnavailableError
from agent.subflows.battle_handler.tools.fight.service import fight as fight_service

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext


def build_fight_tool(context: BattleContext) -> Tool[BattleContext]:
    """Build the fight tool bound to the current battle context."""

    async def fight(
        reason: Annotated[str, Field(min_length=1)],
        move_slot: Annotated[int, Field(ge=0, le=3)],
    ) -> str:
        """Use an available move against the opposing Pokemon.

        The move slot is its zero-based position in the active Pokemon's move
        list. A move with no PP cannot be used. If every move has no PP, use
        slot 0 to make the Pokemon use STRUGGLE.

        Args:
            reason: Brief first-person explanation of why this move is appropriate.
            move_slot: Zero-based slot of the move to use.

        Returns:
            Confirmation of the attempted move.

        Raises:
            ModelRetry: The requested move is unavailable in the latest game state.
        """
        try:
            return await fight_service(
                rolling_memory=context.rolling_memory,
                emulator=context.emulator,
                reason=reason,
                move_slot=move_slot,
            )
        except BattleActionUnavailableError as error:
            raise ModelRetry(str(error)) from error

    return Tool(fight, require_parameter_descriptions=True)
