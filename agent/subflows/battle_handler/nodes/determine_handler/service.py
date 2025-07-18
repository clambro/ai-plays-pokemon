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
from common.types import StateStringBuilderT
from emulator.emulator import YellowLegacyEmulator
from emulator.game_state import YellowLegacyGameState
from llm.schemas import GEMINI_FLASH_2_5
from llm.service import GeminiLLMService
from memory.raw_memory import RawMemory


class DetermineHandlerService:
    """A service that determines the handler for the current game state in the battle."""

    llm_service = GeminiLLMService(model=GEMINI_FLASH_2_5)

    def __init__(
        self,
        iteration: int,
        raw_memory: RawMemory,
        state_string_builder: StateStringBuilderT,
        emulator: YellowLegacyEmulator,
    ) -> None:
        self.iteration = iteration
        self.raw_memory = raw_memory
        self.state_string_builder = state_string_builder
        self.emulator = emulator

    async def determine_handler(self) -> tuple[RawMemory, BattleToolArgs | None]:
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
            return self.raw_memory, None

        args = self._get_legal_args(game_state)
        if not args:
            # Edge case if no Pokemon in the party, zero PP, and either no balls or trainer battle.
            return self.raw_memory, None

        try:
            thoughts, action = await self._choose_args(args, game_state)
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=f'{thoughts} I chose the following battle action: "{action}"',
            )
        except Exception as e:  # noqa: BLE001
            action = None
            self.raw_memory.add_memory(
                iteration=self.iteration,
                content=f"I received the following error when choosing a battle action: {e}",
            )
        return self.raw_memory, action

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
                    for i, p in enumerate(game_state.party)
                    if p != player_pokemon
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
        self,
        args: list[BattleToolArgs],
        game_state: YellowLegacyGameState,
    ) -> tuple[str, BattleToolArgs]:
        """Choose the action to take based on the available arguments."""
        img = self.emulator.get_screenshot()
        actions = "\n".join([f"[{i}]: {a}" for i, a in enumerate(args)])
        prompt = CHOOSE_ARGS_PROMPT.format(
            state=self.state_string_builder(game_state),
            text=game_state.screen.text,
            actions=actions,
        )
        response = await self.llm_service.get_llm_response_pydantic(
            messages=[img, prompt],
            schema=DetermineArgsResponse,
            prompt_name="determine_battle_args",
        )
        return response.thoughts, args[response.index]
