"""Pydantic AI interface for setting the complete goal list."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.formatting.memory import format_goals
from agent.overworld.tools.set_goals.service import GoalChangeError
from agent.overworld.tools.set_goals.service import set_goals as set_goals_service
from agent.overworld.tools.utils import OverworldToolResult, complete_overworld_action
from memory.goals import MAX_GOALS, MIN_GOALS

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_set_goals_tool(
    context: AgentContext,
    *,
    end_turn_on_success: bool = False,
) -> Tool[AgentContext]:
    """Build the complete-list goal-setting tool."""

    async def set_goals(
        goals: Annotated[list[str], Field(min_length=MIN_GOALS, max_length=MAX_GOALS)],
    ) -> OverworldToolResult:
        """Set the complete list of one to four goals.

        Pass the complete list, including any existing goals you want to keep.
        Omitted goals are removed. You may keep the list unchanged when its
        goals remain useful.

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
        goal has changed, been completed, or become irrelevant. Goals guide
        future decisions but do not need to determine your next action.

        Args:
            goals: Complete list of one to four distinct, nonblank goals to keep.

        Returns:
            Fresh screenshot and the complete revised goal list.
        """
        try:
            updated_goals = set_goals_service(
                goals=goals,
                iteration=context.state.iteration,
            )
        except GoalChangeError as error:
            result = str(error)
        else:
            context.state.goals = updated_goals
            if end_turn_on_success:
                context.request_control_handoff()
            result = f"Goals updated.\n\n{format_goals(updated_goals)}"
        return await complete_overworld_action(context, result)

    return Tool(set_goals, require_parameter_descriptions=True)
