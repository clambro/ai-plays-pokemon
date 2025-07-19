from pathlib import Path

import pytest

from agent.subflows.overworld_handler.nodes.use_item.service import UseItemService
from emulator.emulator import YellowLegacyEmulator
from memory.raw_memory import RawMemory


@pytest.mark.integration
async def test_use_item() -> None:
    """Test using an item from the inventory."""
    save_file = Path(__file__).parent / "saves" / "save.state"
    async with YellowLegacyEmulator(
        save_state_path=save_file,
        mute_sound=True,
        headless=True,
    ) as emulator:
        raw_memory = RawMemory()
        raw_memory.add_memory(
            iteration=0,
            content="I want to spray a REPEL to keep wild Pokemon away.",
        )

        service = UseItemService(
            iteration=0,
            raw_memory=raw_memory,
            emulator=emulator,
        )
        raw_memory = await service.use_item()
        await emulator.wait_for_animation_to_finish()

        dialog_box = emulator.get_game_state().get_dialog_box()
        assert dialog_box is not None
        assert dialog_box.top_line == "AAA used"
        assert dialog_box.bottom_line == "REPEL!"
        assert len(raw_memory.pieces) == 1
