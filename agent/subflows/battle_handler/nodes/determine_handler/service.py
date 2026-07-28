"""Business logic for determine handler in the battle subflow."""

from typing import TYPE_CHECKING

from agent.subflows.battle_handler.nodes.determine_handler.prompts import CHOOSE_ARGS_PROMPT
from agent.subflows.battle_handler.nodes.determine_handler.schemas import DetermineArgsResponse
from agent.subflows.battle_handler.schemas import (
    BattleToolArgs,
    FightToolArgs,
    RunToolArgs,
    SwitchPokemonToolArgs,
    ThrowBallToolArgs,
)
from agent.subflows.battle_handler.utils import is_fight_menu_open
from common.enums import BattleType, PokeballItem
from llm.service import OpenAILLMService

if TYPE_CHECKING:
    from PIL.Image import Image

    from common.types import StateStringBuilder
    from emulator.emulator import YellowLegacyEmulator
    from emulator.game_state import YellowLegacyGameState
    from memory.raw_memory import RawMemory

llm_service = OpenAILLMService()


async def determine_handler(
    *,
    iteration: int,
    raw_memory: RawMemory,
    state_string_builder: StateStringBuilder,
    emulator: YellowLegacyEmulator,
) -> tuple[RawMemory, BattleToolArgs | None]:
    """Determine the handler for the current game state in the battle.

    Args:
        iteration: Current agent iteration used to timestamp the decision.
        raw_memory: Recent memory to update with the selected action or error.
        state_string_builder: Formatter for the current game state.
        emulator: Running emulator used to inspect the battle and capture its screen.

    Returns:
        The updated raw memory and selected battle action, or ``None`` when no action can be
        selected.
    """
    game_state, screenshot = await emulator.get_game_state_with_screenshot()
    battle_state = game_state.battle
    if (
        not battle_state.is_in_battle
        or battle_state.battle_type not in [BattleType.TRAINER, BattleType.WILD]
        or not is_fight_menu_open(game_state)
    ):
        return raw_memory, None

    args = _get_legal_args(game_state)
    if not args:
        # Edge case if no Pokemon in the party, zero PP, and either no balls or trainer battle.
        return raw_memory, None

    try:
        thoughts, action = await _choose_args(
            args,
            game_state,
            screenshot,
            state_string_builder=state_string_builder,
        )
        raw_memory.add_memory(
            iteration=iteration,
            content=f'{thoughts} I chose the following battle action: "{action}"',
        )
    except Exception as e:  # noqa: BLE001
        action = None
        raw_memory.add_memory(
            iteration=iteration,
            content=f"I received the following error when choosing a battle action: {e}",
        )
    return raw_memory, action


def _get_legal_args(game_state: YellowLegacyGameState) -> list[BattleToolArgs]:
    """Get the legal actions for a normal trainer or wild battle.

    Args:
        game_state: Current game state with an open fight menu.

    Returns:
        Actions available for the active Pokémon, party, inventory, and battle type.
    """
    args = []
    player_pokemon = game_state.battle.player_pokemon
    if player_pokemon:
        fight_args = [
            FightToolArgs(move_index=index, move_name=move.name)
            for index, move in enumerate(player_pokemon.moves)
            if move.pp > 0
        ]
        if not fight_args:
            fight_args = [FightToolArgs(move_index=0, move_name="STRUGGLE")]
        args.extend(fight_args)
        args.extend(
            [
                SwitchPokemonToolArgs(party_index=i, name=p.name, species=p.species)
                for i, p in enumerate(game_state.party)
                # Can't use p == player_pokemon because the objects update at different times.
                if (p.name, p.species) != (player_pokemon.name, player_pokemon.species) and p.hp > 0
            ]
        )
    if game_state.battle.battle_type == BattleType.WILD:
        for ball in PokeballItem:
            for i, item in enumerate(game_state.inventory.items):
                if item.name == ball.value:
                    args.append(ThrowBallToolArgs(item_index=i, ball=ball))
                    break
        args.append(RunToolArgs())
    return args


async def _choose_args(
    args: list[BattleToolArgs],
    game_state: YellowLegacyGameState,
    screenshot: Image,
    *,
    state_string_builder: StateStringBuilder,
) -> tuple[str, BattleToolArgs]:
    """Choose the action to take based on the available arguments."""
    actions = "\n".join([f"[{i}]: {a}" for i, a in enumerate(args)])
    prompt = CHOOSE_ARGS_PROMPT.format(
        state=state_string_builder(game_state),
        text=game_state.screen.text,
        actions=actions,
    )
    response = await llm_service.get_llm_response_pydantic(
        messages=[screenshot, prompt],
        schema=DetermineArgsResponse,
    )
    return response.thoughts, args[response.index]
