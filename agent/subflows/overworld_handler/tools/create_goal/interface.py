"""Pydantic AI interface for creating goals."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.subflows.overworld_handler.tools.create_goal.service import (
    create_goal as create_goal_service,
)
from agent.subflows.overworld_handler.utils import (
    OverworldToolResult,
    complete_overworld_action,
)
from memory.goals import (  # noqa: TC001  # Pydantic AI evaluates annotations at runtime.
    GoalPriority,
)

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_create_goal_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the goal-creation tool."""

    async def create_goal(
        goal: Annotated[str, Field(min_length=1)],
        priority: GoalPriority,
    ) -> OverworldToolResult:
        """Create one new goal worth pursuing.

        There are three priority levels for goals:

        - Primary: These represent major milestones like gym battles or other
          key objectives required to progress the game. You must have exactly
          one primary goal at a time, and you should change it sparingly.
        - Secondary: These directly support the primary goal. Examples include
          finding a specific item required for the primary goal, or navigating
          to a specific map to get to the primary goal. You can have up to
          three secondary goals at once. There is no minimum requirement.
          Achieving a secondary goal should be a meaningful step towards
          achieving the primary goal. Secondary goals must support the current
          primary goal.
        - Tertiary: These are not related to the primary goal, but could still
          be important to pursue. Examples include catching Pokemon, training
          your Pokemon, healing your Pokemon, buying items, or exploring an
          area. You can have up to three tertiary goals at once. There is no
          minimum requirement.

        A good goal must be SMART:

        - Specific: The goal must be clearly defined and not vague.
          - Bad: "Level up my Pokemon"
          - Good: "Level up my [pokemon] to level [level]"
        - Measurable: The goal must have clear criteria for success.
          - Bad: "Complete Pewter City"
          - Good: "Defeat Brock in the Pewter City Gym and collect the
            BOULDERBADGE"
        - Achievable: The goal must be possible within the confines of the
          game.
          - Bad: "Get my whole team to level 100" (not possible before
            becoming the Champion due to the level cap)
          - Good: "Catch a [pokemon] in [location]" (assuming that you have
            seen that Pokemon at that location)
        - Relevant: The goal must be relevant to your ultimate goal of
          collecting all eight badges and becoming the Champion. Completing
          the Pokedex is not relevant to this goal, except insofar as you need
          to catch Pokemon to build your team.
          - Bad: "Catch five Magikarp" (silly and pointless)
          - Good: "Catch a [pokemon] in [location] and add it to my team to
            help me defeat [major opponent]"
        - Time-bound: The least-relevant of the SMART criteria for your
          purposes, but try to ensure that your goals have clear temporal
          boundaries when relevant.
          - Suboptimal: "Heal my Pokemon at the [location] Pokemon Center"
          - Good: "Heal my Pokemon at the [location] Pokemon Center before
            heading to [next location]"

        New goals must be distinct from existing goals. Do not create a goal
        that is essentially the same as another goal, even at a different
        priority. Base new goals on your experience in the game as recorded in
        memory or player information, not on prior Pokemon knowledge, which is
        prone to error.

        Create a goal only when recent events warrant it and the goal is not
        already in your list. You must have at least one goal at any given
        time. Try to have no more than five active goals at once.

        Args:
            goal: Complete text of the specific new goal, without an index.
            priority: Importance of the new goal: Primary, Secondary, or
                Tertiary.

        Returns:
            Fresh screenshot and the complete revised goal list.
        """
        goals = create_goal_service(
            goals=context.state.goals,
            goal=goal,
            priority=priority,
        )
        context.state.goals = goals
        result = f"Created goal:\n{goals}"
        return await complete_overworld_action(context, result)

    return Tool(create_goal, require_parameter_descriptions=True)
