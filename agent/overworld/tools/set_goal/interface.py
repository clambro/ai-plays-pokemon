"""Pydantic AI interface for setting or clearing one goal."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.formatting.memory import format_goals
from agent.overworld.tools.set_goal.service import GoalChangeError
from agent.overworld.tools.set_goal.service import set_goal as set_goal_service
from agent.overworld.tools.utils import OverworldToolResult, complete_overworld_action

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_set_goal_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the indexed goal-setting tool."""

    async def set_goal(
        index: Annotated[int, Field(ge=0)],
        goal: Annotated[str | None, Field(min_length=1)],
    ) -> OverworldToolResult:
        """Set or clear one longer-term goal.

        Pass goal text to replace an existing goal or append at the next unused
        index. Pass null to remove an existing goal; later goals will shift down
        to keep the list contiguous. The goal list can contain up to four goals.

        Goals are longer-term objectives or concerns worth remembering across
        many decisions, not individual button presses or routine movement. Write
        each goal in the first person and describe one specific, achievable
        outcome. Keep distinct priorities in separate goals rather than
        combining them, but do not add goals merely to fill every available slot.

        Base goals only on current structured information, observed game text,
        or recorded memory. Do not invent locations, characters, items, or
        objectives from general Pokemon knowledge or assumptions about future
        progression.

        Use this tool when an important priority is missing or when an existing
        goal has changed, been completed, or become irrelevant. Replace an
        outdated goal directly when another priority should take its place; use
        null when it should simply be removed. Goals guide future decisions but
        do not need to determine your next action.

        Args:
            index: Existing goal index, or the next unused index when appending.
            goal: Complete goal text, or null to remove the indexed goal.

        Returns:
            Fresh screenshot and the complete revised goal list.
        """
        try:
            goals = set_goal_service(
                goals=context.state.goals,
                index=index,
                goal=goal,
                iteration=context.state.iteration,
            )
        except GoalChangeError as error:
            result = str(error)
        else:
            context.state.goals = goals
            result = f"Goals updated.\n\n{format_goals(goals)}"
        return await complete_overworld_action(context, result)

    return Tool(set_goal, require_parameter_descriptions=True)
