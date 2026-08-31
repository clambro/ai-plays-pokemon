"""Prompts for the Pydantic AI battle agent."""

from typing import TYPE_CHECKING

from agent.battle.formatting import format_available_pokeballs, format_battle_info
from agent.formatting.game_state import format_party_info, format_player_info
from agent.formatting.memory import format_goals, format_rolling_memory
from common.enums import BattleType

if TYPE_CHECKING:
    from agent.context import AgentContext
    from emulator.game_state import GameState

BATTLE_DECISION_PROMPT = """
You are in a Pokemon battle. The screenshot provided above shows the battle at entry. After each tool call, its returned context is the freshest state and supersedes earlier observations. Briefly explain your reasoning in first person as ordinary response text, then use exactly one tool to take the next battle action. Every response must include one tool call; the agent loop ends automatically when the game exits battle mode.

{state}

Here is the decoded onscreen text from the game's memory. It preserves recognized text glyphs and cursor positions, but graphical tiles may be omitted. Use it to read labels and navigate menus. If multiple cursors "▷" and "▶" are present, the active cursor is "▶".
<onscreen_text>
{text}
</onscreen_text>
Use the screenshot when the decoded text is incomplete or visual context matters.

{battle_guidance}
""".strip()


def _format_battle_guidance(game_state: GameState) -> str:
    """Format strategy that applies to the current kind of battle."""
    battle_type = game_state.battle.battle_type
    if battle_type not in {BattleType.TRAINER, BattleType.WILD}:
        return ""

    guidance = "Using a move or voluntarily switching Pokemon consumes the turn. Switching gives the opponent an opportunity to attack the Pokemon switched in. Experience is granted only to Pokemon used in the battle, provided they have not fainted and are not at the level cap."
    if battle_type == BattleType.WILD:
        guidance += " If you are not deliberately training a particular party member and do not intend to catch this Pokemon, running is the default. A favorable matchup, easy victory, or generally useful experience is not by itself a reason to fight. An unsuccessful capture attempt or failed escape also gives the opponent an opportunity to attack."
    return guidance


def build_battle_decision_prompt(
    context: AgentContext,
    initial_game_state: GameState,
) -> str:
    """Build the prompt for the battle-entry observation."""
    sections = (
        format_rolling_memory(context.state.rolling_memory),
        format_goals(context.state.goals),
        format_player_info(initial_game_state),
        format_party_info(initial_game_state),
        format_available_pokeballs(initial_game_state),
        format_battle_info(initial_game_state),
    )
    state = "\n\n".join(section for section in sections if section)
    return BATTLE_DECISION_PROMPT.format(
        state=state,
        text=initial_game_state.screen.text,
        battle_guidance=_format_battle_guidance(initial_game_state),
    ).strip()
