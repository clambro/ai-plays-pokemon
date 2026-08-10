"""Prompts for the Pydantic AI text agent."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState

TEXT_DECISION_PROMPT = """
There is actionable text on the screen. The screenshot provided above shows the screen at entry. After each tool call, its returned context is the freshest state and supersedes earlier observations. Briefly explain your reasoning in first person as ordinary response text, then use exactly one tool to take the next action. Every response must include one tool call; the agent loop ends automatically when the game exits text mode or enters a battle.

{state}

Here is the game memory's representation of the onscreen text. The text you see below is exactly what the game is displaying on the screen, but the formatting may be somewhat messed up because it is not rendering images. Use it to help you understand the text on the screen, as well as the position of any cursors. If you see multiple cursors "▷" and "▶", you are probably in a nested menu. The active cursor is always "▶". This is a more reliable way to navigate menus than the screenshot, but keep the screenshot in mind as well.
<onscreen_text>
{text}
</onscreen_text>
Onscreen text includes only recognized glyphs. Graphical elements may be omitted, so use the screenshot when the text is incomplete or visual context matters.
""".strip()


def build_text_decision_prompt(
    context: AgentContext,
    initial_game_state: GameState,
) -> str:
    """Build the prompt for the initial actionable text screen."""
    return TEXT_DECISION_PROMPT.format(
        state=context.state.to_prompt_string(initial_game_state),
        text=initial_game_state.screen.text,
    )
