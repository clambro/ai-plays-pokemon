"""Pydantic AI interface for deleting one goal."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.overworld.tools.delete_goal.service import (
    GoalNotFoundError,
)
from agent.overworld.tools.delete_goal.service import (
    delete_goal as delete_goal_service,
)
from agent.overworld.utils import (
    OverworldToolResult,
    complete_overworld_action,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_delete_goal_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the single-goal deletion tool."""

    async def delete_goal(
        index: Annotated[int, Field(ge=0)],
    ) -> OverworldToolResult:
        """Delete one completed or abandoned goal.

        Deletion represents either completing a goal or deciding that you no
        longer want to chase it. Use this tool only for one of those reasons.
        Goals are referred to by the indices in the current goal list.

        Do not delete a goal merely to revise its text or priority; update it
        instead. Do not assume that you have accomplished a goal until memory
        or current player information makes that certain. You must have at
        least one goal at any given time, including exactly one primary goal,
        so plan any related creation or update before deleting a goal that is
        still required.

        Args:
            index: Zero-based index of the completed or abandoned goal to
                delete.

        Returns:
            Fresh screenshot and either the deleted goal plus the complete
            revised goal list, or a validation error explaining why no change
            was made.
        """
        try:
            goals, deleted_goal = delete_goal_service(
                goals=context.state.goals,
                index=index,
            )
        except GoalNotFoundError as error:
            result = str(error)
        else:
            context.state.goals = goals
            result = f"Deleted goal:\n{deleted_goal}\n\nUpdated goals:\n{goals}"

        return await complete_overworld_action(context, result)

    return Tool(delete_goal, require_parameter_descriptions=True)
