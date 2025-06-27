from loguru import logger

from agent.subflows.battle_handler.schemas import (
    BattleToolArgs,
    FightToolArgs,
    RunToolArgs,
    SwitchPokemonToolArgs,
    ThrowBallToolArgs,
)
from agent.subflows.battle_handler.utils import is_fight_menu_open
from common.enums import BattleType, PokeballItem
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState


class DetermineHandlerService:
    """A service that determines the handler for the current game state in the battle."""

    def __init__(self, emulator: YellowLegacyEmulator) -> None:
        self.emulator = emulator

    async def determine_handler(self) -> BattleToolArgs | None:
        """
        Determine the handler for the current game state in the battle.

        :return: The raw memory with the decision added.
        """
        game_state = self.emulator.get_game_state()
        battle_state = game_state.battle
        if (
            not battle_state.is_in_battle
            or battle_state.battle_type not in [BattleType.TRAINER, BattleType.WILD]
            or not is_fight_menu_open(game_state)
        ):
            return None

        args = self._get_legal_args(game_state)
        if not args:
            # Edge case if no Pokemon in the party, zero PP, and either no balls or trainer battle.
            return None

        logger.info(f"The following battle options are available: {[str(a) for a in args]}")
        return None

    @staticmethod
    def _get_legal_args(game_state: YellowLegacyGameState) -> list[BattleToolArgs]:
        """
        Get the legal arguments for the current game state. This assumes that we're in a normal
        trainer or wild battle.

        :param game_state: The game state.
        :return: The legal arguments.
        """
        args = []
        player_pokemon = game_state.battle.player_pokemon
        if player_pokemon:
            args.extend(
                [
                    FightToolArgs(move_index=i, move_name=move.name)
                    for i, move in enumerate(player_pokemon.moves)
                    if move.pp > 0
                ]
            )
            args.extend(
                [
                    SwitchPokemonToolArgs(party_index=i, name=p.name, species=p.species)
                    for i, p in enumerate(game_state.party, start=1)
                    if p != player_pokemon
                ]
            )
        if game_state.battle.battle_type == BattleType.WILD:
            for ball in PokeballItem:
                for i, item in enumerate(game_state.inventory.items):
                    if item.name == ball.name:
                        args.append(ThrowBallToolArgs(item_index=i, ball=ball))
                        break
            args.append(RunToolArgs())
        return args
