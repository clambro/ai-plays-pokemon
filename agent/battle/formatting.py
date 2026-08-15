"""Model-facing formatting for battle state."""

from typing import TYPE_CHECKING

from common.enums import BattleType, PokeballItem

if TYPE_CHECKING:
    from emulator.game_state import GameState


def format_battle_info(game_state: GameState) -> str:
    """Format the current battle state for the battle agent."""
    battle = game_state.battle
    if not battle.is_in_battle:
        return ""
    if battle.battle_type == BattleType.OTHER:
        return "<battle_info>You are in a special battle, possibly a cutscene.</battle_info>"

    out = "<battle_info>\n"
    if battle.battle_type == BattleType.SAFARI_ZONE:
        out += "You are in a Safari Zone battle.\n"
    elif battle.battle_type == BattleType.TRAINER:
        out += "You are in a trainer battle.\n"
    elif battle.battle_type == BattleType.WILD:
        out += "You are in a battle against a wild Pokemon.\n"

    if battle.player_pokemon and battle.battle_type != BattleType.SAFARI_ZONE:
        out += "<player_pokemon>\n"
        out += f"Name: {battle.player_pokemon.name}\n"
        out += f"Species: {battle.player_pokemon.species}\n"
        out += f"Level: {battle.player_pokemon.level}\n"
        out += f"HP: {battle.player_pokemon.hp} / {battle.player_pokemon.max_hp}\n"
        out += f"Status Ailment: {battle.player_pokemon.status}\n"
        out += "<moves>\n"
        for slot, move in enumerate(battle.player_pokemon.moves):
            disabled = " [DISABLED]" if slot == battle.disabled_move_slot else ""
            out += f"- Slot {slot}: {move.name} (PP: {move.pp}){disabled}\n"
        out += "</moves>\n"
        out += "</player_pokemon>\n"

    if battle.enemy_pokemon:
        out += "<enemy_pokemon>\n"
        out += f"Name: {battle.enemy_pokemon.name}\n"
        out += f"Level: {battle.enemy_pokemon.level}\n"
        out += f"HP Percentage: {battle.enemy_pokemon.hp_pct:.0f}%\n"
        out += f"Status Ailment: {battle.enemy_pokemon.status}\n"
        out += "</enemy_pokemon>\n"

    if battle.num_enemy_pokemon:
        out += (
            f"The enemy trainer has {battle.num_enemy_pokemon} Pokemon remaining, "
            "including the one you're battling.\n"
        )

    out += "</battle_info>"
    return out


def format_available_pokeballs(game_state: GameState) -> str:
    """Format Poke Balls currently available during a wild battle."""
    if game_state.battle.battle_type != BattleType.WILD:
        return ""

    pokeball_names = {ball.value for ball in PokeballItem}
    available_balls = [
        f"- {item.name} (x{item.quantity})"
        for item in game_state.inventory.items
        if item.name in pokeball_names
    ]
    if not available_balls:
        return ""
    return "Available Poke Balls:\n" + "\n".join(available_balls)
