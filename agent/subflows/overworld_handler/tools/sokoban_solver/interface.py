"""Pydantic AI interface for deterministic Sokoban solving."""

from typing import TYPE_CHECKING

from pydantic_ai import Tool

from agent.subflows.overworld_handler.tools.sokoban_solver.service import SokobanSolverService

if TYPE_CHECKING:
    from agent.subflows.overworld_handler.context import OverworldContext


def build_sokoban_solver_tool(context: OverworldContext) -> Tool[OverworldContext]:
    """Build the Sokoban tool bound to the current overworld context."""

    async def sokoban_solver() -> str:
        """Solve the current boulder puzzle deterministically.

        The Sokoban solver tool will automatically solve the onscreen Sokoban
        puzzle for you, or inform you if the puzzle is not currently solvable
        (likely meaning that you need to explore more).

        Returns:
            Confirmation that the solver ran.
        """
        state = context.state
        if state.rolling_memory is None:
            raise ValueError("Rolling memory is not set")
        if state.current_map is None:
            raise ValueError("Current map is not set")
        service = SokobanSolverService(
            emulator=context.emulator,
            current_map=state.current_map,
            rolling_memory=state.rolling_memory,
        )
        await service.solve()
        return "Ran the Sokoban solver."

    return Tool(sokoban_solver, require_parameter_descriptions=True)
