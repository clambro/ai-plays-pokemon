"""Pydantic AI interface for attempting to leave a battle."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import ModelRetry, Tool

from agent.subflows.battle_handler.tools.errors import BattleActionUnavailableError
from agent.subflows.battle_handler.tools.run.service import run as run_service

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext


def build_run_tool(context: BattleContext) -> Tool[BattleContext]:
    """Build the run tool bound to the current battle context."""

    async def run(
        reason: Annotated[str, Field(min_length=1)],
    ) -> str:
        """Attempt to run from the current battle.

        Args:
            reason: Brief first-person explanation of why running is appropriate.

        Returns:
            Confirmation of the escape attempt.

        Raises:
            ModelRetry: Running is unavailable in the latest game state.
        """
        try:
            return await run_service(
                rolling_memory=context.rolling_memory,
                emulator=context.emulator,
                reason=reason,
            )
        except BattleActionUnavailableError as error:
            raise ModelRetry(str(error)) from error

    return Tool(run, require_parameter_descriptions=True)
