"""Tests for the throw ball tool service."""

from pathlib import Path

import pytest

from agent.battle.tools.throw_ball.service import throw_ball
from common.enums import PokeballItem
from emulator.control_events import ControlBoundary
from emulator.emulator import Emulator


@pytest.mark.integration
async def test_throw_pokeball() -> None:
    """Test throwing a Poke Ball in battle."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with Emulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        game_state = await emulator.get_game_state()

        # Verify that the initial state is as expected.
        assert game_state.battle.is_in_battle

        assert any(item.name == PokeballItem.POKE_BALL for item in game_state.inventory.items), (
            "Poke Ball not found in inventory"
        )

        await throw_ball(
            emulator=emulator,
            ball_type=PokeballItem.POKE_BALL,
        )

        game_state, boundary = await emulator.get_game_state_with_control_boundary()
        assert game_state.battle.is_in_battle
        assert boundary == ControlBoundary.TEXT_INPUT_READY
