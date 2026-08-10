"""Pydantic AI interface for attempting to leave a battle."""

from typing import TYPE_CHECKING

from pydantic_ai import Tool

from agent.battle.tools.errors import BattleActionUnavailableError
from agent.battle.tools.run.service import run as run_service
from agent.battle.utils import (
    BattleToolResult,
    complete_battle_action,
    refresh_battle_observation,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_run_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the run tool bound to the current battle context."""

    async def run() -> BattleToolResult:
        """Attempt to run from the current battle.

        Returns:
            Fresh battle context after the escape attempt.
        """
        try:
            result = await run_service(emulator=context.emulator)
        except BattleActionUnavailableError as error:
            return await refresh_battle_observation(
                context,
                action_result=str(error),
            )
        return await complete_battle_action(context, result)

    return Tool(run, require_parameter_descriptions=True)
