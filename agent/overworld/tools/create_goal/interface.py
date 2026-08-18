"""Pydantic AI interface for creating goals."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.formatting.memory import format_goals
from agent.overworld.tools.create_goal.service import (
    GoalLimitReachedError,
)
from agent.overworld.tools.create_goal.service import (
    create_goal as create_goal_service,
)
from agent.overworld.tools.utils import (
    OverworldToolResult,
    complete_overworld_action,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_create_goal_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the goal-creation tool."""

    async def create_goal(
        goal: Annotated[str, Field(min_length=1)],
    ) -> OverworldToolResult:
        """Create one longer-term goal worth keeping in mind.

        The goal list has a fixed capacity. If the list is full, update or
        delete an existing goal before creating another.

        Create goals only from objectives justified by current structured
        information, observed game text, or recorded memory. Do not invent
        goals from general Pokemon knowledge, examples in these instructions,
        or assumptions about future game progression. If your current context
        has not introduced a location, character, item, or objective, it must
        not appear in a goal.

        Strongly avoid the word "and" in goal text because it usually joins
        multiple goals that should be split. This is guidance, not an absolute
        prohibition when "and" is genuinely part of one indivisible outcome.
        A good goal is specific, achievable, relevant to your current
        progress, and important enough to remember across many decisions.

        New goals must be distinct from existing goals. Do not create a goal
        that is essentially the same as another goal.

        Regularly reflect on your current objectives and concerns. When several
        priorities are active, create a separate goal for each of them. Keep
        the list useful and current, but do not create goals merely to fill
        every available slot. Write every goal in the first person, just like
        your reasoning and memories.

        Args:
            goal: Complete text of the new goal, without an index.

        Returns:
            Fresh screenshot and the complete revised goal list.
        """
        try:
            updated_goals = create_goal_service(
                goals=context.state.goals,
                goal=goal,
                iteration=context.state.iteration,
            )
        except GoalLimitReachedError as error:
            result = str(error)
        else:
            context.state.goals = updated_goals
            result = f"Created goal.\n\n{format_goals(updated_goals)}"
        return await complete_overworld_action(context, result)

    return Tool(create_goal, require_parameter_descriptions=True)
