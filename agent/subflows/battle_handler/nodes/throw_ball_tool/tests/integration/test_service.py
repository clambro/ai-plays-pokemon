"""Tests for the throw ball tool service."""

import asyncio
from pathlib import Path

import pytest

from agent.subflows.battle_handler.nodes.throw_ball_tool.service import throw_ball
from agent.subflows.battle_handler.schemas import ThrowBallToolArgs
from common.enums import PokeballItem
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory


@pytest.mark.integration
async def test_throw_pokeball() -> None:
    """Test throwing a Poke Ball in battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()

        # Verify that the initial state is as expected.
        assert game_state.battle.is_in_battle

        # Find the Poke Ball in the inventory.
        pokeball_index = None
        for i, item in enumerate(game_state.inventory.items):
            if item.name == PokeballItem.POKE_BALL:
                pokeball_index = i
                break
        assert pokeball_index is not None, "Poke Ball not found in inventory"

        raw_memory = await throw_ball(
            iteration=0,
            raw_memory=RawMemory(),
            tool_args=ThrowBallToolArgs(item_index=pokeball_index, ball=PokeballItem.POKE_BALL),
            emulator=emulator,
        )
        await asyncio.sleep(0.1)  # Enough time to change frames, but not to catch the pokemon.

        game_state = await emulator.get_game_state()
        assert "POKé BALL!" in game_state.screen.text  # Used Poke Ball text.
        assert len(raw_memory.pieces) == 1
