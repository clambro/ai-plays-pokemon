"""Pydantic AI interface for creating goals."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.formatting.memory import format_goals
from agent.overworld.tools.create_goal.service import (
    PrimaryGoalAlreadyExistsError,
    SecondaryGoalLimitReachedError,
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
        *,
        is_primary: bool,
    ) -> OverworldToolResult:
        """Create one new goal worth pursuing.

        Set ``is_primary`` to true only for your one primary goal. The primary
        goal represents one major outcome already established by your current
        context. It is not a plan or a list of every step required to reach that
        outcome. You should normally maintain one primary goal and keep it
        stable while its intended outcome remains relevant. You cannot create a
        new primary goal while one exists; either update the current goal's
        text, or delete it and create its replacement in a subsequent tool call.

        Set ``is_primary`` to false for secondary goals. Each secondary goal
        represents one discrete prerequisite or useful step that directly
        supports the primary goal. You can have up to three secondary goals at
        once. There is no minimum requirement.

        Create goals only from objectives justified by current structured
        information, observed game text, or recorded memory. Do not invent
        goals from general Pokemon knowledge, examples in these instructions,
        or assumptions about future game progression. If your current context
        has not introduced a location, character, item, or objective, it must
        not appear in a goal.

        Every goal should contain one outcome. Strongly avoid the word "and" in
        goal text because it usually joins multiple goals that should be split.
        This is guidance, not an absolute prohibition when "and" is genuinely
        part of a single indivisible outcome. A good goal must be specific,
        measurable, achievable, and relevant to your current progress. Goals
        should also be incremental. Do not make "defeat the elite four" your
        goal when you have just started the game.

        New goals must be distinct from existing goals. Do not create a goal
        that is essentially the same as another goal.

        Create a goal only when recent events warrant it and the goal is not
        already in your list. You should normally have a primary goal, but do
        not create secondary goals merely to fill the available slots. Write
        every goal in the first person, just like your reasoning and memories.

        Args:
            goal: Complete text of the specific new goal, without an index.
            is_primary: Whether this is the primary goal rather than a
                secondary goal.

        Returns:
            Fresh screenshot and the complete revised goal list.
        """
        try:
            goals = create_goal_service(
                goals=context.state.goals,
                goal=goal,
                is_primary=is_primary,
                iteration=context.state.iteration,
            )
        except (SecondaryGoalLimitReachedError, PrimaryGoalAlreadyExistsError) as error:
            result = str(error)
        else:
            context.state.goals = goals
            result = f"Created goal.\n\n{format_goals(goals)}"
        return await complete_overworld_action(context, result)

    return Tool(create_goal, require_parameter_descriptions=True)
