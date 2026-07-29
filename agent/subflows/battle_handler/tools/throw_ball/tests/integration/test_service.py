"""Tests for the throw ball tool service."""

import asyncio
from pathlib import Path

import pytest

from agent.subflows.battle_handler.tools.throw_ball.service import throw_ball
from common.enums import PokeballItem
from emulator.emulator import YellowLegacyEmulator


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
        assert any(item.name == PokeballItem.POKE_BALL for item in game_state.inventory.items), (
            "Poke Ball not found in inventory"
        )

        await throw_ball(
            emulator=emulator,
            ball_type=PokeballItem.POKE_BALL,
        )
        await asyncio.sleep(0.1)  # Enough time to change frames, but not to catch the pokemon.

        game_state = await emulator.get_game_state()
        assert "POKé BALL!" in game_state.screen.text  # Used Poke Ball text.
