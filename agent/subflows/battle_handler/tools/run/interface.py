"""Pydantic AI interface for attempting to leave a battle."""

from typing import TYPE_CHECKING

from pydantic_ai import ModelRetry, Tool

from agent.subflows.battle_handler.tools.errors import BattleActionUnavailableError
from agent.subflows.battle_handler.tools.run.service import run as run_service
from agent.subflows.battle_handler.utils import (
    BattleToolResult,
    complete_battle_action,
    refresh_battle_observation,
)

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext


def build_run_tool(context: BattleContext) -> Tool[BattleContext]:
    """Build the run tool bound to the current battle context."""

    async def run() -> BattleToolResult:
        """Attempt to run from the current battle.

        Returns:
            Fresh battle context after the escape attempt.

        Raises:
            ModelRetry: Running is unavailable in the latest game state.
        """
        try:
            result = await run_service(
                rolling_memory=context.state.rolling_memory,
                emulator=context.emulator,
            )
        except BattleActionUnavailableError as error:
            retry_context = await refresh_battle_observation(
                context,
                action_result=str(error),
            )
            raise ModelRetry(retry_context) from error
        return await complete_battle_action(context, result)

    return Tool(run, require_parameter_descriptions=True)
