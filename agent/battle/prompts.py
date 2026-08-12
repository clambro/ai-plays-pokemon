"""Prompts for the Pydantic AI battle agent."""

from typing import TYPE_CHECKING

from agent.battle.formatting import format_battle_info
from agent.formatting.game_state import format_player_info

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState

BATTLE_DECISION_PROMPT = """
You are in a Pokemon battle. The screenshot provided above shows the battle at entry. After each tool call, its returned context is the freshest state and supersedes earlier observations. Briefly explain your reasoning in first person as ordinary response text, then use exactly one tool to take the next battle action. Every response must include one tool call; the agent loop ends automatically when the game exits battle mode.

{state}

Here is the game memory's representation of the onscreen text. The text you see below is exactly what the game is displaying on the screen, but the formatting may be somewhat messed up because it is not rendering images. Use it to help you understand the text on the screen, as well as the position of any cursors. If you see multiple cursors "▷" and "▶", you are probably in a nested menu. The active cursor is always "▶". This is a more reliable way to navigate menus than the screenshot, but keep the screenshot in mind as well.
<onscreen_text>
{text}
</onscreen_text>
Onscreen text includes only recognized glyphs. Graphical elements may be omitted, so use the screenshot when the text is incomplete or visual context matters.

Fighting, voluntarily switching Pokemon, throwing a Poke Ball, and attempting to run all use up your turn, giving the opponent an opportunity to attack. In particular, switching gives the opponent a free attack against the Pokemon you switch in. Experience is granted only to Pokemon used in the battle, provided they have not fainted and are not at the level cap.

Note: If you keep seeing the text "There's no will to fight" over and over again, it means that you are trying to switch into a fainted Pokemon. You cannot do this. You must switch to a Pokemon that has not fainted. If you are seeing this text, at least one of your Pokemon is still able to fight. Use the directional buttons to pick a different Pokemon to switch to.
""".strip()


def build_battle_decision_prompt(
    context: AgentContext,
    initial_game_state: GameState,
) -> str:
    """Build the prompt for the battle-entry observation."""
    state = "\n\n".join(
        (
            str(context.state.rolling_memory),
            str(context.state.goals),
            format_player_info(initial_game_state),
            format_battle_info(initial_game_state),
        ),
    )
    return BATTLE_DECISION_PROMPT.format(
        state=state,
        text=initial_game_state.screen.text,
    )
