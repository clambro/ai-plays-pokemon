"""Tests for the use item service."""

from pathlib import Path

import pytest

from agent.subflows.overworld_handler.tools.use_item.service import UseItemService
from emulator.emulator import YellowLegacyEmulator
from memory.rolling_memory import RollingMemory


@pytest.mark.integration
async def test_use_item() -> None:
    """Test using an item from the inventory."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        item_index = next(
            index
            for index, item in enumerate((await emulator.get_game_state()).inventory.items)
            if item.name == "REPEL"
        )
        rolling_memory = RollingMemory()
        rolling_memory.add_memory(
            content="I want to spray a REPEL to keep wild Pokemon away.",
        )

        service = UseItemService(
            rolling_memory=rolling_memory,
            emulator=emulator,
        )
        rolling_memory = await service.use_item(item_index)
        await emulator.wait_for_animation_to_finish()

        dialog_box = (await emulator.get_game_state()).get_dialog_box()
        assert dialog_box is not None
        assert dialog_box.top_line == "AAA used"
        assert dialog_box.bottom_line == "REPEL!"
        assert len(rolling_memory.raw_blocks) == 1
