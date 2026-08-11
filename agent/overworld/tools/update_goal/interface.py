"""Pydantic AI interface for updating one goal."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.overworld.tools.update_goal.service import (
    GoalNotFoundError,
)
from agent.overworld.tools.update_goal.service import (
    update_goal as update_goal_service,
)
from agent.overworld.tools.utils import (
    OverworldToolResult,
    complete_overworld_action,
)
from memory.goals import (  # noqa: TC001  # Pydantic AI evaluates annotations at runtime.
    GoalPriority,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_update_goal_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the single-goal update tool."""

    async def update_goal(
        index: Annotated[int, Field(ge=0)],
        goal: Annotated[str, Field(min_length=1)],
        priority: GoalPriority,
    ) -> OverworldToolResult:
        """Revise one existing goal after acquiring new information.

        Use this tool to edit a goal's text, priority, or both while continuing
        to pursue the same objective. Goals are referred to by the indices in
        the current goal list. Supply the complete replacement goal, including
        all information that should remain after the update.

        Do not use this tool for a goal that has been completed or that you no
        longer want to pursue; delete that goal instead. Update primary goals
        sparingly. If a primary goal changes, you must also update or delete
        secondary goals that are no longer relevant, because every secondary
        goal must directly support the current primary goal.

        The revised goal must remain specific, measurable, achievable,
        relevant to becoming Champion, and time-bound when appropriate. It
        must remain distinct from every other goal. Base the revision on your
        experience recorded in memory or current player information, not
        prior Pokemon knowledge, which is prone to error.

        Args:
            index: Zero-based index of the existing goal to revise.
            goal: Complete replacement text for the goal.
            priority: Complete replacement priority: Primary, Secondary, or
                Tertiary.

        Returns:
            Fresh screenshot and either the complete revised goal list or a
            validation error explaining why no change was made.
        """
        try:
            goals = update_goal_service(
                goals=context.state.goals,
                index=index,
                goal=goal,
                priority=priority,
            )
        except GoalNotFoundError as error:
            result = str(error)
        else:
            context.state.goals = goals
            result = f"Updated goal:\n{goals}"

        return await complete_overworld_action(context, result)

    return Tool(update_goal, require_parameter_descriptions=True)
