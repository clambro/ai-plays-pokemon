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
        goal represents one major outcome such as earning a badge or completing
        another key objective required to progress through the game. It is not
        a plan or a list of every step required to reach that outcome. You
        should normally maintain one primary goal and keep it stable while its
        intended outcome remains relevant. You cannot create a new primary goal
        while one exists; either update the current goal's text, or delete it
        and create its replacement in a subsequent tool call.

        Set ``is_primary`` to false for secondary goals. Each secondary goal
        represents one discrete prerequisite or useful step that directly
        supports the primary goal, such as catching a new Pokemon, finding a
        required item, preparing for a major battle, or reaching the objective's
        location. You can have up to three secondary goals at once. There is no
        minimum requirement.

        Every goal should contain one outcome. Strongly avoid the word "and" in
        goal text because it usually joins multiple goals that should be split.
        This is guidance, not an absolute prohibition when "and" is genuinely
        part of a single indivisible outcome.

        - Bad primary goal: "I will heal my team, catch another Pokemon, reach
          Pewter City, and earn the BOULDERBADGE."
        - Good primary goal: "I will earn the BOULDERBADGE from Brock."
        - Good secondary goal: "I will heal my team at the Pewter City Pokemon
          Center."
        - Good secondary goal: "I will catch a Pokemon that has a super
          effective attack against Brock's team."

        A good goal must be SMART:

        - Specific: The goal must be clearly defined and not vague.
          - Bad: "Level up my Pokemon"
          - Good: "Level up my [pokemon] to level [level]"
        - Measurable: The goal must have clear criteria for success.
          - Bad: "Complete Pewter City"
          - Good: "Earn the BOULDERBADGE from Brock"
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
          - Good: "Catch a [pokemon] in [location] to help me defeat [major
            opponent]"
        - Time-bound: The least-relevant of the SMART criteria for your
          purposes, but try to ensure that your goals have clear temporal
          boundaries when relevant.
          - Suboptimal: "Train my Pokemon"
          - Good: "Train my [pokemon] to level [level] before challenging
            [major opponent]"

        New goals must be distinct from existing goals. Do not create a goal
        that is essentially the same as another goal. Base new goals on your
        experience in the game as recorded in memory or player information,
        not on prior Pokemon knowledge, which is prone to error.

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
