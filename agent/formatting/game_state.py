"""Shared model-facing formatting for parsed gameplay state."""

from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image
from pydantic_ai import BinaryContent

from common.enums import PokeballItem

if TYPE_CHECKING:
    from emulator.game_state import GameState
    from emulator.parsers.pokemon import Pokemon


def build_screenshot_content(screenshot: Image.Image) -> BinaryContent:
    """Encode a screenshot at four times its resolution without altering the source image."""
    image_buffer = BytesIO()
    screenshot.resize(
        (screenshot.width * 4, screenshot.height * 4),
        resample=Image.Resampling.NEAREST,
    ).save(image_buffer, format="PNG")
    return BinaryContent(
        data=image_buffer.getvalue(),
        media_type="image/png",
        vendor_metadata={"detail": "original"},
    )


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
        moves = ", ".join(move.name for move in pokemon.moves)
        out += f"- {pokemon.name} ({pokemon.species}, Level {pokemon.level}): {moves}\n"
    out += "</pc_pokemon>"
    max_box_pokemon = 20
    if len(game_state.pc_pokemon) >= max_box_pokemon:
        out += (
            "\n\nWarning: Your active PC box is full. If your party is also full, you cannot"
            " catch Pokemon. Change to a box with space at a PC or withdraw Pokemon to make room."
        )
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
            out += f"- {move.name} (Type: {move.type}, PP: {move.pp})\n"
        out += "</moves>\n"
        out += f"</pokemon_{index}>\n"
    return out
