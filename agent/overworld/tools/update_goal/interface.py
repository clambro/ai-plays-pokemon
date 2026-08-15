"""Pydantic AI interface for updating one goal."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.formatting.memory import format_goals
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

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_update_goal_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the single-goal update tool."""

    async def update_goal(
        index: Annotated[int, Field(ge=0)],
        goal: Annotated[str, Field(min_length=1)],
    ) -> OverworldToolResult:
        """Revise one existing goal after acquiring new information.

        Use this tool to replace a goal's text. Goals are referred to by the
        indices in the current goal list. Supply the complete replacement goal,
        including all information that should remain after the update. Updating
        a goal cannot change whether it is primary; delete it and create a
        replacement to change that designation.

        Do not use this tool for a goal that has been completed or that you no
        longer want to pursue; delete that goal instead. Update the primary
        goal only when new information meaningfully changes its intended
        outcome or success criterion. Do not update a goal merely to reword it,
        record progress, append another task, or keep it recent. Keep the
        primary goal stable while its outcome remains relevant; represent the
        steps toward it with secondary goals. You should maintain exactly one
        primary goal and may have up to three secondary goals.

        The revised goal must remain specific, measurable, achievable, and
        relevant to your current progress. It must describe one outcome
        and remain distinct from every other goal. Strongly avoid the word
        "and" because it usually joins multiple goals that should be separate.

        Base every revision only on current structured information, observed
        game text, or recorded memory. Do not add a location, character, item,
        or objective inferred from general Pokemon knowledge or anticipated
        future progression. Write the complete replacement goal in the first
        person, just like your reasoning and memories.

        Args:
            index: Zero-based index of the existing goal to revise.
            goal: Complete replacement text for the goal.

        Returns:
            Fresh screenshot and either the complete revised goal list or a
            validation error explaining why no change was made.
        """
        try:
            goals = update_goal_service(
                goals=context.state.goals,
                index=index,
                goal=goal,
                iteration=context.state.iteration,
            )
        except GoalNotFoundError as error:
            result = str(error)
        else:
            context.state.goals = goals
            result = f"Updated goal.\n\n{format_goals(goals)}"

        return await complete_overworld_action(context, result)

    return Tool(update_goal, require_parameter_descriptions=True)
