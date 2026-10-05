"""Integration coverage for selecting Pokemon through PC lists."""

import asyncio
from pathlib import Path

import pytest

from agent.context import AgentContext
from agent.dialog import settle_dialog
from agent.state import AgentState
from agent.text.tools.errors import TextActionUnavailableError
from agent.text.tools.select_pc_pokemon.service import select_pc_pokemon
from common.enums import Button
from emulator.control_events import ControlBoundary
from emulator.emulator import Emulator

_SAVE_FILE = Path(__file__).parent / "saves" / "deposit.state"


@pytest.mark.integration
@pytest.mark.parametrize(("starting_index", "target_index"), [(0, 5), (4, 0)])
async def test_select_and_deposit_pokemon(starting_index: int, target_index: int) -> None:
    """Scroll either way, stop before transferring, then deposit the chosen Pokemon."""
    async with Emulator(save_state_path=_SAVE_FILE, mute_sound=True, headless=True) as emulator:
        async with asyncio.timeout(15):
            for _ in range(starting_index):
                await emulator.press_button(Button.DOWN)
            before = await emulator.get_game_state()
            expected = before.party[target_index]

            await select_pc_pokemon(emulator=emulator, pokemon_index=target_index)
            selected = await emulator.get_game_state()
            assert selected.party == before.party
            assert selected.pc_pokemon == before.pc_pokemon

            await emulator.press_button(Button.A)
            await emulator.advance_text_dialog()
            after = await emulator.get_game_state()

    assert after.party == before.party[:target_index] + before.party[target_index + 1 :]
    assert len(after.pc_pokemon) == len(before.pc_pokemon) + 1
    assert after.pc_pokemon[-1].name == expected.name
    assert after.pc_pokemon[-1].species == expected.species


@pytest.mark.integration
async def test_select_and_withdraw_scrolled_box_pokemon(tmp_path: Path) -> None:
    """Settle the deposit confirmation, then withdraw a box entry beyond the visible rows."""
    async with Emulator(save_state_path=_SAVE_FILE, mute_sound=True, headless=True) as emulator:
        async with asyncio.timeout(15):
            context = AgentContext(state=AgentState(folder=tmp_path), emulator=emulator)
            await select_pc_pokemon(emulator=emulator, pokemon_index=0)
            await emulator.press_button(Button.A)
            confirmation, boundary = await emulator.get_game_state_with_control_boundary()
            assert boundary == ControlBoundary.TEXT_INPUT_READY
            assert confirmation.is_text_on_screen(ignore_dialog_box=True)
            settlement = await settle_dialog(context)
            assert settlement.control_boundary == ControlBoundary.MENU_READY
            await emulator.press_button(Button.UP)
            await emulator.press_button(Button.A)
            before = await emulator.get_game_state()
            target_index = len(before.pc_pokemon) - 1
            expected = before.pc_pokemon[target_index]

            await select_pc_pokemon(emulator=emulator, pokemon_index=target_index)
            selected = await emulator.get_game_state()
            assert selected.party == before.party
            assert selected.pc_pokemon == before.pc_pokemon

            await emulator.press_button(Button.A)
            await emulator.advance_text_dialog()
            after = await emulator.get_game_state()

    assert len(after.party) == len(before.party) + 1
    assert after.party[-1].name == expected.name
    assert after.party[-1].species == expected.species
    assert after.pc_pokemon == before.pc_pokemon[:target_index]


@pytest.mark.integration
async def test_invalid_selection_does_not_operate_the_menu() -> None:
    """Reject nonexistent entries and action submenus without pressing buttons."""
    async with Emulator(save_state_path=_SAVE_FILE, mute_sound=True, headless=True) as emulator:
        async with asyncio.timeout(15):
            before = await emulator.get_game_state()
            for index in (-1, len(before.party)):
                with pytest.raises(TextActionUnavailableError):
                    await select_pc_pokemon(emulator=emulator, pokemon_index=index)
                rejected = await emulator.get_game_state()
                assert rejected.screen.menu_item_index == before.screen.menu_item_index
                assert rejected.screen.list_scroll_offset == before.screen.list_scroll_offset

            await select_pc_pokemon(emulator=emulator, pokemon_index=0)
            selected = await emulator.get_game_state()
            with pytest.raises(TextActionUnavailableError):
                await select_pc_pokemon(emulator=emulator, pokemon_index=1)
            after = await emulator.get_game_state()

    assert after.screen.menu_item_index == selected.screen.menu_item_index
    assert after.screen.list_scroll_offset == selected.screen.list_scroll_offset
    assert after.party == before.party
    assert after.pc_pokemon == before.pc_pokemon
