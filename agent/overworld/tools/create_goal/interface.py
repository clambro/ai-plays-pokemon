"""Pydantic AI interface for creating goals."""

from typing import TYPE_CHECKING, Annotated

from pydantic import Field
from pydantic_ai import Tool

from agent.formatting.memory import format_goals
from agent.overworld.tools.create_goal.service import (
    OtherGoalLimitReachedError,
    PrimaryGoalAlreadyExistsError,
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
        goal represents a major milestone such as a gym battle or another key
        objective required to progress through the game. You should normally
        maintain one primary goal and change it sparingly. You cannot create a
        new primary goal while one exists; either update the current goal's
        text, or delete it and create its replacement in a subsequent tool
        call.

        Set ``is_primary`` to false for other goals. Other goals may directly
        support the primary goal, such as finding a required item or navigating
        to the primary objective, or may be independently useful, such as
        catching or training Pokemon, healing, buying items, or exploring an
        area. You can have up to five other goals at once. There is no minimum
        requirement.

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
        that is essentially the same as another goal. Base new goals on your
        experience in the game as recorded in memory or player information,
        not on prior Pokemon knowledge, which is prone to error.

        Create a goal only when recent events warrant it and the goal is not
        already in your list. You should normally have a primary goal, but do
        not create other goals merely to fill the available slots.

        Args:
            goal: Complete text of the specific new goal, without an index.
            is_primary: Whether this is the one primary goal rather than an
                other goal.

        Returns:
            Fresh screenshot and the complete revised goal list.
        """
        try:
            goals = create_goal_service(
                goals=context.state.goals,
                goal=goal,
                is_primary=is_primary,
            )
        except (OtherGoalLimitReachedError, PrimaryGoalAlreadyExistsError) as error:
            result = str(error)
        else:
            context.state.goals = goals
            result = f"Created goal.\n\n{format_goals(goals)}"
        return await complete_overworld_action(context, result)

    return Tool(create_goal, require_parameter_descriptions=True)
