"""Shared model-facing formatting for parsed gameplay state."""

from typing import TYPE_CHECKING

from common.enums import PokeballItem

if TYPE_CHECKING:
    from emulator.game_state import GameState
    from emulator.parsers.pokemon import Pokemon


def format_player_info(game_state: GameState) -> str:
    """Format the player's core state for agent prompts."""
    out = "<player_info>\n"
    if game_state.player.name:
        out += f"Name: {game_state.player.name}\n"
    out += f"Money: {game_state.player.money}\n"
    if game_state.player.badges:
        out += f"Badges Earned: {', '.join(game_state.player.badges)}\n"
    out += f"Current Level Cap: {game_state.player.level_cap}\n"
    out += "</player_info>"
    return out


def format_party_info(game_state: GameState) -> str:
    """Format the player's current party for agent prompts."""
    if not game_state.party:
        return ""
    out = "<party>\n"
    out += "These are the Pokemon in your party, in their current order.\n"
    out += _format_pokemon_list(game_state.party, game_state.player.level_cap)
    out += "</party>"
    return out


def format_inventory_info(game_state: GameState) -> str:
    """Format the player's current inventory for agent prompts."""
    out = "<inventory>\n"
    if game_state.inventory.items:
        for index, item in enumerate(game_state.inventory.items):
            out += f"[{index}] {item.name} (x{item.quantity})\n"
    else:
        out += "Your inventory is empty.\n"
    out += "</inventory>"
    pokeball_names = {ball.value for ball in PokeballItem}
    if not any(item.name in pokeball_names for item in game_state.inventory.items):
        out += "\n\nNote: You have no Poke Balls. They can be purchased at Poke Marts."
    return out


def format_pc_info(game_state: GameState) -> str:
    """Format Pokemon stored in the active PC box for agent prompts."""
    if not game_state.pc_pokemon:
        return ""
    out = "<pc_pokemon>\n"
    out += "Stored in the active PC box, not in the party:\n"
    for pokemon in game_state.pc_pokemon:
        pokemon_type = f"{pokemon.type1}/{pokemon.type2}" if pokemon.type2 else pokemon.type1
        moves = ", ".join(f"{move.name} ({move.pp} PP)" for move in pokemon.moves)
        out += (
            f"- {pokemon.name} ({pokemon.species}, Level {pokemon.level}, {pokemon_type}): "
            f"{moves}\n"
        )
    out += "</pc_pokemon>"
    return out


def _format_pokemon_list(pokemon_list: list[Pokemon], level_cap: int) -> str:
    """Format party Pokemon in their current order."""
    out = ""
    for index, pokemon in enumerate(pokemon_list):
        out += f"<pokemon_{index}>\n"
        out += f"Name: {pokemon.name}\n"
        out += f"Species: {pokemon.species}\n"
        if pokemon.type2:
            out += f"Type: {pokemon.type1} / {pokemon.type2}\n"
        else:
            out += f"Type: {pokemon.type1}\n"
        out += f"Level: {pokemon.level}"
        if pokemon.level >= level_cap:
            out += (
                " (AT LEVEL CAP: Can be used, but any experience it gains is wasted and will not"
                " be applied.)"
            )
        out += "\n"
        out += f"HP: {pokemon.hp} / {pokemon.max_hp}\n"
        out += f"Status Ailment: {pokemon.status}\n"
        out += "<moves>\n"
        for move in pokemon.moves:
            out += f"- {move.name} (PP: {move.pp})\n"
        out += "</moves>\n"
        out += f"</pokemon_{index}>\n"
    return out
