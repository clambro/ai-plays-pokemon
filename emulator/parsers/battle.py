"""Parser for battle data in Pokémon Yellow memory."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from common.enums import BattleType
from emulator.parsers.pokemon import (
    EnemyPokemon,
    Pokemon,
    parse_enemy_battle_pokemon,
    parse_player_battle_pokemon,
)

if TYPE_CHECKING:
    from pyboy import PyBoyMemoryView

_WILD_BATTLE_FLAG = 1
_TRAINER_BATTLE_FLAG = 2
_NORMAL_BATTLE_TYPE_FLAG = 0
_SAFARI_ZONE_BATTLE_FLAG = 2


class Battle(BaseModel):
    """The state of the current battle."""

    is_in_battle: bool
    battle_type: BattleType | None
    player_pokemon: Pokemon | None
    enemy_pokemon: EnemyPokemon | None
    num_enemy_pokemon: int | None = Field(ge=0, le=100)
    disabled_move_slot: int | None = Field(default=None, ge=0, le=3)

    model_config = ConfigDict(frozen=True)


def parse_battle_state(mem: PyBoyMemoryView) -> Battle:
    """Parse the current battle state from emulator memory.

    Args:
        mem: Current PyBoy memory view.

    Returns:
        An immutable battle snapshot.
    """
    is_battle_flag = mem[0xD057]
    battle_type_flag = mem[0xD05A]
    is_in_battle = is_battle_flag in {_WILD_BATTLE_FLAG, _TRAINER_BATTLE_FLAG}
    if not is_in_battle:
        return Battle(
            is_in_battle=False,
            battle_type=None,
            player_pokemon=None,
            enemy_pokemon=None,
            num_enemy_pokemon=None,
            disabled_move_slot=None,
        )

    # Note that both flags are used to determine the battle type.
    if battle_type_flag == _SAFARI_ZONE_BATTLE_FLAG:
        battle_type = BattleType.SAFARI_ZONE
    elif battle_type_flag != _NORMAL_BATTLE_TYPE_FLAG:
        battle_type = BattleType.OTHER
    elif is_battle_flag == _WILD_BATTLE_FLAG:
        battle_type = BattleType.WILD
    elif is_battle_flag == _TRAINER_BATTLE_FLAG:
        battle_type = BattleType.TRAINER
    else:
        battle_type = BattleType.OTHER  # Should be inaccessible, but just in case.

    player_pokemon = (
        parse_player_battle_pokemon(mem) if battle_type != BattleType.SAFARI_ZONE else None
    )
    if battle_type == BattleType.TRAINER and player_pokemon is None:
        enemy_pokemon = None  # Enemy hasn't been sent out yet.
    else:
        enemy_pokemon = parse_enemy_battle_pokemon(mem)

    num_enemy_pokemon = mem[0xD89B] if battle_type == BattleType.TRAINER else None
    if num_enemy_pokemon:
        num_remaining_enemy_pokemon = 0
        for i in range(num_enemy_pokemon):
            increment = i * 0x2C
            enemy_hp = (mem[0xD8A4 + increment] << 8) | mem[0xD8A5 + increment]
            if enemy_hp > 0:
                num_remaining_enemy_pokemon += 1
        num_enemy_pokemon = num_remaining_enemy_pokemon

    disabled_move_number = mem[0xD06D] >> 4
    disabled_move_slot = disabled_move_number - 1 if disabled_move_number else None

    return Battle(
        is_in_battle=is_in_battle,
        battle_type=battle_type,
        player_pokemon=player_pokemon,
        enemy_pokemon=enemy_pokemon,
        num_enemy_pokemon=num_enemy_pokemon,
        disabled_move_slot=disabled_move_slot,
    )
