from pyboy import PyBoyMemoryView
from pydantic import BaseModel, ConfigDict, Field

from common.enums import BattleType
from emulator.parsers.pokemon import (
    EnemyPokemon,
    Pokemon,
    parse_enemy_battle_pokemon,
    parse_player_battle_pokemon,
)

_WILD_BATTLE_FLAG = 1
_TRAINER_BATTLE_FLAG = 2
_SAFARI_ZONE_BATTLE_FLAG = 2


class Battle(BaseModel):
    """The state of the current battle."""

    is_in_battle: bool
    battle_type: BattleType | None
    player_pokemon: Pokemon | None
    enemy_pokemon: EnemyPokemon | None
    num_enemy_pokemon: int | None = Field(ge=0, le=100)

    model_config = ConfigDict(frozen=True)


def parse_battle_state(mem: PyBoyMemoryView) -> Battle:
    """
    Create a new battle state from a snapshot of the memory.

    :param mem: The PyBoyMemoryView instance to create the battle state from.
    :return: A new battle state.
    """
    is_battle_flag = mem[0xD057]
    battle_type_flag = mem[0xD057]
    is_in_battle = is_battle_flag > 0
    if not is_in_battle:
        return Battle(
            is_in_battle=False,
            battle_type=None,
            player_pokemon=None,
            enemy_pokemon=None,
            num_enemy_pokemon=None,
        )

    # Note that both flags are used to determine the battle type.
    if is_battle_flag == _WILD_BATTLE_FLAG:
        battle_type = BattleType.WILD
    elif is_battle_flag == _TRAINER_BATTLE_FLAG:
        battle_type = BattleType.TRAINER
    elif battle_type_flag == _SAFARI_ZONE_BATTLE_FLAG:
        battle_type = BattleType.SAFARI_ZONE
    else:
        battle_type = BattleType.OTHER

    player_pokemon = (
        parse_player_battle_pokemon(mem) if battle_type != BattleType.SAFARI_ZONE else None
    )
    if battle_type == BattleType.TRAINER and player_pokemon is None:
        enemy_pokemon = None  # Enemy hasn't been sent out yet.
    else:
        enemy_pokemon = parse_enemy_battle_pokemon(mem)

    num_enemy_pokemon = mem[0xD89B] if battle_type == BattleType.TRAINER else None

    return Battle(
        is_in_battle=is_in_battle,
        battle_type=battle_type,
        player_pokemon=player_pokemon,
        enemy_pokemon=enemy_pokemon,
        num_enemy_pokemon=num_enemy_pokemon,
    )
