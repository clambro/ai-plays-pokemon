"""Overworld tool for requesting occasional strategic advice."""

from typing import TYPE_CHECKING

from loguru import logger
from pydantic_ai import Tool

from agent.formatting.game_state import build_screenshot_content
from agent.formatting.memory import format_goals
from agent.overworld.map_view import build_current_map_view
from agent.overworld.prompts import format_overworld_state
from agent.overworld.tools.consult_advisor import service
from common.constants import ADVISOR_ADVICE_LABEL
from overworld_map.service import prepare_overworld_map

if TYPE_CHECKING:
    from agent.context import AgentContext

_COOLDOWN_ITERATIONS = 100


def build_consult_advisor_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the consultation tool with a persisted 100-iteration cooldown."""

    async def consult_advisor(question: str) -> str:
        """Ask for strategic advice when you remain stuck or repeatedly fail to progress.

        Use this for a fresh assessment and a concrete suggestion for what to
        do next when your own attempts are not resolving the blockage. The
        advisor receives your current game state, screenshot, goals, and memory,
        and can inspect known maps. It returns advice and can replace your goals
        if it feels that is necessary. It does not move you or act in the game.
        Consultations are available at most once every 100 iterations, so use
        them sparingly rather than as a routine part of gameplay.

        Args:
            question: Describe the blockage and what you need help deciding.

        Returns:
            Advice and the updated goals, or an explanation that consultation is unavailable.
        """
        last_advice = context.state.last_advice_iteration
        if last_advice is not None and context.state.iteration - last_advice < _COOLDOWN_ITERATIONS:
            return (
                "Consultation is available again at iteration "
                f"{last_advice + _COOLDOWN_ITERATIONS}."
            )
        context.state.last_advice_iteration = context.state.iteration
        try:
            game_state, screenshot = await context.emulator.get_game_state_with_screenshot()
            current_map = await prepare_overworld_map(context.state.iteration, game_state)
            map_view = build_current_map_view(current_map, game_state)
            advisor = service.build_advisor_agent(context, game_state)
            result = await advisor.run(
                [
                    build_screenshot_content(screenshot),
                    format_overworld_state(context, map_view, game_state),
                    question,
                ],
                deps=context,
            )
        except Exception as error:  # noqa: BLE001
            logger.opt(exception=error).warning(
                "Advisor consultation failed; continuing ordinary gameplay."
            )
            return "Consultation failed. Continue using your current state and available tools."
        advice = f"{ADVISOR_ADVICE_LABEL} {result.output}\n\n{format_goals(context.state.goals)}"
        context.state.rolling_memory.add_memory(advice)
        return advice

    return Tool(consult_advisor, require_parameter_descriptions=True)
