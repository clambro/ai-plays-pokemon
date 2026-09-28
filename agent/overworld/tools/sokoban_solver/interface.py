"""Pydantic AI interface for deterministic Sokoban solving."""

from typing import TYPE_CHECKING

from pydantic_ai import Tool

from agent.overworld.tools.sokoban_solver.service import solve_sokoban
from agent.overworld.tools.utils import (
    OverworldToolResult,
    complete_overworld_action,
)

if TYPE_CHECKING:
    from agent.context import AgentContext
    from overworld_map.schemas import OverworldMap


def build_sokoban_solver_tool(
    context: AgentContext,
    current_map: OverworldMap,
) -> Tool[AgentContext]:
    """Build the Sokoban tool bound to the current overworld context."""

    async def sokoban_solver() -> OverworldToolResult:
        """Solve the known boulder puzzles on the current map deterministically.

        Try this tool before pushing boulders manually. It continues through the goals
        it can solve, reporting how many it completed and how many solvable goals remain
        if interrupted. More exploration or boulders from another floor may be needed
        for goals that are not currently solvable.

        Returns:
            Fresh screenshot and the actual solver result.
        """
        result = await solve_sokoban(
            iteration=context.state.iteration,
            emulator=context.emulator,
            current_map=current_map,
            rolling_memory=context.state.rolling_memory,
        )
        return await complete_overworld_action(context, result)

    return Tool(sokoban_solver, require_parameter_descriptions=True)
