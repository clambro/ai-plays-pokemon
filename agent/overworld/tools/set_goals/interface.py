"""Pydantic AI interface for setting the complete goal list."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.formatting.memory import format_goals
from agent.overworld.tools.set_goals.service import GoalChangeError
from agent.overworld.tools.set_goals.service import set_goals as set_goals_service
from agent.overworld.tools.utils import OverworldToolResult, complete_overworld_action
from memory.goals import MAX_GOALS

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_set_goals_tool(
    context: AgentContext,
    *,
    end_turn_on_success: bool = False,
) -> Tool[AgentContext]:
    """Build the complete-list goal-setting tool."""

    async def set_goals(
        goals: Annotated[list[str | None], Field(min_length=MAX_GOALS, max_length=MAX_GOALS)],
    ) -> OverworldToolResult:
        """Replace your current goals using three slots, with null for unused slots.

        Pass the complete list, including any existing goals you want to keep.
        Omitted goals are removed. You may keep the list unchanged when its
        goals remain useful.

        Set specific, achievable goals with clear completion conditions. Prefer meaningful
        milestones over individual next steps. Goals are not ongoing play-style rules, nor
        are they immediate next actions. Write them in the imperative and keep distinct
        priorities separate. Do not add goals merely to fill slots; leave unused slots null.

        Base goals only on current structured information, observed game text,
        or recorded memory. Do not invent locations, characters, items, or
        objectives from general Pokemon knowledge or assumptions about future
        progression.

        Use this tool when an important priority is missing or when an existing
        goal has changed, been completed, or become irrelevant. Goals guide
        future decisions but do not need to determine your next action.

        Goal examples:

        Bad goal: Collect an ordinary item at <coordinates>.
        Bad goal: Interact with <unexamined NPC>.
        Reasoning: These are each single exploration steps, not the broader outcome.
        Better goal: Completely explore <area>.

        Bad goal: Keep party members healthy and well trained.
        Reasoning: This is ongoing advice with no completion condition.
        Better goal: Heal my party before attempting <major battle>.

        Bad goal: Continue progressing towards the next badge.
        Reasoning: This describes ongoing progress instead of a specific challenge to complete.
        Better goal: Face off against <gym leader name> to get the <next badge>.

        Args:
            goals: Exactly three entries in rough order of priority, each a nonblank goal or null.

        Returns:
            Fresh screenshot and the complete revised goal list.
        """
        try:
            updated_goals = set_goals_service(
                goals=[goal for goal in goals if goal is not None],
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
