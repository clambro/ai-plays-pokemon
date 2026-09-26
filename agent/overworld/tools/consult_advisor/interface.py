"""Overworld tool for requesting occasional strategic advice."""

from typing import TYPE_CHECKING

from loguru import logger
from pydantic_ai import Tool

from agent.formatting.game_state import build_screenshot_content
from agent.overworld.map_view import build_current_map_view
from agent.overworld.prompts import format_overworld_state
from agent.overworld.tools.consult_advisor import agent
from common.constants import ADVISOR_ADVICE_LABEL
from overworld_map.service import prepare_overworld_map

if TYPE_CHECKING:
    from agent.context import AgentContext


def build_consult_advisor_tool(context: AgentContext) -> Tool[AgentContext]:
    """Build the consultation tool for an eligible overworld run."""

    async def consult_advisor(progress_report: str) -> str:
        """Give the advisor a progress report for a strategic review.

        Use this voluntarily when your own attempts are not resolving a
        blockage and you need a fresh assessment of what to do next.

        The advisor receives your current game state, screenshot, goals, and
        memory, and can inspect known maps. It returns a strategic second
        opinion but does not move you or act in the game. Its advice is generally
        helpful but fallible, so assess it against current game data.

        Voluntary consultations are available at most once every 100 iterations,
        so use them when you need help rather than as part of routine gameplay.
        Periodically, consultation is required to review your progress.

        Args:
            progress_report: Give a high-level assessment of your approach and
                how it is going. Mention any blockage or decision you need help
                with. The advisor already has your game state, party, goals, and
                history, so focus on your assessment rather than repeating them.

        Returns:
            Fallible strategic advice, or an explanation that consultation failed.
        """
        context.state.last_advice_iteration = context.state.iteration
        context.request_control_handoff()
        try:
            game_state, screenshot = await context.emulator.get_game_state_with_screenshot()
            current_map = await prepare_overworld_map(context.state.iteration, game_state)
            map_view = build_current_map_view(current_map, game_state)
            advisor = agent.build_advisor_agent(context, game_state)
            result = await advisor.run(
                [
                    build_screenshot_content(screenshot),
                    format_overworld_state(context, map_view, game_state),
                    progress_report,
                ],
                deps=context,
            )
        except Exception as error:  # noqa: BLE001
            logger.opt(exception=error).warning(
                "Advisor consultation failed; continuing ordinary gameplay."
            )
            return "Consultation failed. Continue using your current state and available tools."
        advice = (
            f"{ADVISOR_ADVICE_LABEL} This advice is generally helpful but fallible; assess it"
            f" against current game data.\n{result.output}"
        )
        context.state.rolling_memory.add_memory(advice)
        return advice

    return Tool(consult_advisor, require_parameter_descriptions=True)
