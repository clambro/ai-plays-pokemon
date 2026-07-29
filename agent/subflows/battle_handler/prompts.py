"""Prompts for the Pydantic AI battle agent."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext

BATTLE_DECISION_PROMPT = """
You are in a Pokemon battle. The screenshot provided above is the current game screen. Use the press_buttons tool once to proceed with the battle.

{state}

Here is the game memory's representation of the onscreen text. The text you see below is exactly what the game is displaying on the screen, but the formatting may be somewhat messed up because it is not rendering images. Use it to help you understand the text on the screen, as well as the position of any cursors. If you see multiple cursors "▷" and "▶", you are probably in a nested menu. The active cursor is always "▶". This is a more reliable way to navigate menus than the screenshot, but keep the screenshot in mind as well.
<onscreen_text>
{text}
</onscreen_text>
If you see garbled, nonsensical text in the onscreen text, it is because the game is rendering an image, which the memory stores as text. If this is the case, use the screenshot to help you better understand what is going on.

Note: If you keep seeing the text "There's no will to fight" over and over again, it means that you are trying to switch into a fainted Pokemon. You cannot do this. You must switch to a Pokemon that has not fainted. If you are seeing this text, at least one of your Pokemon is still able to fight. Use the directional buttons to pick a different Pokemon to switch to.
""".strip()


def build_battle_decision_prompt(context: BattleContext) -> str:
    """Build the prompt for the current battle observation."""
    state = "\n\n".join(
        (
            str(context.rolling_memory),
            str(context.long_term_memory),
            str(context.goals),
            context.game_state.player_info,
            context.game_state.battle_info,
        ),
    )
    return BATTLE_DECISION_PROMPT.format(
        state=state,
        text=context.game_state.screen.text,
    )
