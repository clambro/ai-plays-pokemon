"""Prompts for the Pydantic AI battle agent."""

from typing import TYPE_CHECKING

from common.enums import BattleType, PokeballItem

if TYPE_CHECKING:
    from agent.subflows.battle_handler.context import BattleContext
    from emulator.game_state import YellowLegacyGameState

BATTLE_DECISION_PROMPT = """
You are in a Pokemon battle. The screenshot provided above shows the battle at entry. After each tool call, its returned context is the freshest state and supersedes earlier observations. Briefly explain your reasoning in first person as ordinary response text, then use exactly one tool to take the next battle action. Every response must include a tool call; the agent loop ends automatically when the game exits battle mode.

{state}

Here is the game memory's representation of the onscreen text. The text you see below is exactly what the game is displaying on the screen, but the formatting may be somewhat messed up because it is not rendering images. Use it to help you understand the text on the screen, as well as the position of any cursors. If you see multiple cursors "▷" and "▶", you are probably in a nested menu. The active cursor is always "▶". This is a more reliable way to navigate menus than the screenshot, but keep the screenshot in mind as well.
<onscreen_text>
{text}
</onscreen_text>
If you see garbled, nonsensical text in the onscreen text, it is because the game is rendering an image, which the memory stores as text. If this is the case, use the screenshot to help you better understand what is going on.

Fighting, voluntarily switching Pokemon, throwing a Poke Ball, and attempting to run all use up your turn, giving the opponent an opportunity to attack. In particular, switching gives the opponent a free attack against the Pokemon you switch in. Experience is granted only to Pokemon used in the battle, provided they have not fainted and are not at the level cap.

Note: If you keep seeing the text "There's no will to fight" over and over again, it means that you are trying to switch into a fainted Pokemon. You cannot do this. You must switch to a Pokemon that has not fainted. If you are seeing this text, at least one of your Pokemon is still able to fight. Use the directional buttons to pick a different Pokemon to switch to.
""".strip()


def build_battle_decision_prompt(
    context: BattleContext,
    initial_game_state: YellowLegacyGameState,
) -> str:
    """Build the prompt for the battle-entry observation."""
    state = "\n\n".join(
        (
            str(context.state.rolling_memory),
            str(context.state.long_term_memory),
            str(context.state.goals),
            initial_game_state.player_info,
            initial_game_state.battle_info,
        ),
    )
    return BATTLE_DECISION_PROMPT.format(
        state=state,
        text=initial_game_state.screen.text,
    )


def build_battle_tool_result(
    game_state: YellowLegacyGameState,
    *,
    action_result: str,
    dialog: str = "",
) -> str:
    """Build the fresh context returned by a battle tool."""
    sections = [action_result]
    if dialog:
        sections.append(f'Battle dialog: "{dialog}"')
    available_balls: list[str] = []
    if game_state.battle.battle_type == BattleType.WILD:
        pokeball_names = {ball.value for ball in PokeballItem}
        available_balls = [
            f"- {item.name} (x{item.quantity})"
            for item in game_state.inventory.items
            if item.name in pokeball_names
        ]
    sections.extend(
        (
            game_state.party_info,
            "Available Poke Balls:\n" + "\n".join(available_balls) if available_balls else "",
            game_state.battle_info,
            "Current onscreen text:\n" + game_state.screen.text,
        ),
    )
    return "\n\n".join(section for section in sections if section)
