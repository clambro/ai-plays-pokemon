"""Fly-menu behavior against a local, ignored Pokémon Yellow save state."""

import asyncio
from pathlib import Path

import pytest

from agent.overworld.tools.fly.service import fly
from common.enums import MapId
from emulator.emulator import Emulator
from memory.rolling_memory.schemas import RollingMemory

_SAVE_FILE = Path(__file__).parent / "saves" / "fly.state"


@pytest.mark.integration
async def test_fly_to_visited_city() -> None:
    """A visited Fly destination is selected and the player arrives there."""
    async with Emulator(save_state_path=_SAVE_FILE, mute_sound=True, headless=True) as emulator:
        result = await asyncio.wait_for(
            fly(rolling_memory=RollingMemory(), emulator=emulator, destination=MapId.CELADON_CITY),
            timeout=30,
        )
        game_state = await emulator.get_game_state()

    assert "I flew to CELADON_CITY" in result
    assert game_state.map.id == MapId.CELADON_CITY


@pytest.mark.integration
async def test_cannot_fly_to_unvisited_city() -> None:
    """A town missing from the game's visited list is not selected or travelled to."""
    async with Emulator(save_state_path=_SAVE_FILE, mute_sound=True, headless=True) as emulator:
        original_map = (await emulator.get_game_state()).map.id
        result = await asyncio.wait_for(
            fly(
                rolling_memory=RollingMemory(),
                emulator=emulator,
                destination=MapId.INDIGO_PLATEAU,
            ),
            timeout=30,
        )
        game_state = await emulator.get_game_state()

    assert "not available in the Fly destination menu" in result
    assert game_state.map.id == original_map
