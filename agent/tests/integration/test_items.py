"""Integration coverage for item use from the overworld and an open bag."""

import asyncio
from pathlib import Path

import pytest

from agent.context import AgentContext
from agent.dialog import settle_dialog
from agent.items import use_item
from agent.state import AgentState
from agent.utils import move_cursor
from common.enums import Button
from emulator.emulator import Emulator

_SAVE_FILE = Path(__file__).parent / "saves" / "items.state"


@pytest.mark.integration
@pytest.mark.parametrize("open_bag", [False, True])
async def test_use_recovery_items(tmp_path: Path, *, open_bag: bool) -> None:
    """Heal and cure status from either entry point, leaving target decisions to the caller."""
    async with Emulator(save_state_path=_SAVE_FILE, mute_sound=True, headless=True) as emulator:
        async with asyncio.timeout(20):
            context = AgentContext(state=AgentState(folder=tmp_path), emulator=emulator)
            if open_bag:
                await emulator.press_button(Button.START)
                screen = (await emulator.get_game_state()).screen
                await move_cursor(emulator, screen.menu_item_index, 2)
                await emulator.press_button(Button.A)

            for item_name in ("HYPER POTION", "FULL HEAL"):
                before = await emulator.get_game_state()
                item_index = next(
                    index
                    for index, item in enumerate(before.inventory.items)
                    if item.name == item_name
                )
                await use_item(emulator=emulator, item_index=item_index)
                target_selection = await emulator.get_game_state()
                assert target_selection.party == before.party
                assert target_selection.inventory == before.inventory
                await use_item(emulator=emulator, item_index=item_index)
                rejected = await emulator.get_game_state()
                assert rejected.party == target_selection.party
                assert rejected.inventory == target_selection.inventory
                assert rejected.screen.menu_item_index == target_selection.screen.menu_item_index

                await move_cursor(emulator, target_selection.screen.menu_item_index, 0)
                await emulator.press_button(Button.A)
                settlement = await settle_dialog(context)
                after = settlement.game_state
                assert after.screen.is_bag_menu
                assert len(after.inventory.items) == len(before.inventory.items) - 1

                if item_name == "HYPER POTION":
                    assert after.party[0].hp == after.party[0].max_hp
                    assert after.party[0].hp > before.party[0].hp
                else:
                    assert before.party[0].status == "ASLEEP"
                    assert after.party[0].status is None
