"""Prompts for the Pydantic AI text agent."""

from typing import TYPE_CHECKING

from agent.formatting.game_state import format_player_info
from agent.formatting.memory import format_goals, format_rolling_memory

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState

TEXT_DECISION_PROMPT = """
There is actionable text on the screen. The screenshot provided above shows the screen at entry. After each tool call, its returned context is the freshest state and supersedes earlier observations. Briefly explain your reasoning in first person as ordinary response text, then use exactly one tool to take the next action. Every response must include one tool call; the agent loop ends automatically when the game exits text mode or enters a battle.

{state}

Here is the decoded onscreen text from the game's memory. It preserves recognized text glyphs and cursor positions, but graphical tiles may be omitted. Use it to read labels and navigate menus. If multiple cursors "▷" and "▶" are present, the active cursor is "▶".
<onscreen_text>
{text}
</onscreen_text>
Use the screenshot when the decoded text is incomplete or visual context matters.
""".strip()


def build_text_decision_prompt(
    context: AgentContext,
    initial_game_state: GameState,
) -> str:
    """Build the prompt for the initial actionable text screen."""
    state = "\n\n".join(
        (
            format_rolling_memory(context.state.rolling_memory),
            format_goals(context.state.goals),
            format_player_info(initial_game_state),
        ),
    )
    return TEXT_DECISION_PROMPT.format(
        state=state,
        text=initial_game_state.screen.text,
    )
