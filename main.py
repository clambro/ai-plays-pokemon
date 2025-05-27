import argparse
import asyncio
from datetime import datetime
from pathlib import Path

import aiofiles
import aiofiles.os
from loguru import logger

from agent.app import build_agent_workflow
from agent.state import AgentState
from backup.service import create_backup, load_backup
from common.constants import ITERATIONS_PER_BACKUP, OUTPUTS_FOLDER
from database.db_config import init_fresh_db
from emulator.emulator import YellowLegacyEmulator


async def main(
    rom_path: str,
    mute_sound: bool,
    backup_folder: Path | None = None,
) -> None:
    """
    Get the emulator ticking on an async thread, and iteratively run the agent.

    :param rom_path: The path to the ROM file.
    :param state_path: Optional path to load a saved state from.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUTPUTS_FOLDER / timestamp
    await aiofiles.os.makedirs(folder, exist_ok=True)

    if backup_folder:
        state = await load_backup(backup_folder)
        emulator_state = state.emulator_save_state
    else:
        await init_fresh_db()
        state = AgentState(folder=folder)
        emulator_state = None

    async with YellowLegacyEmulator(rom_path, emulator_state, mute_sound=mute_sound) as emulator:
        try:
            while True:
                workflow = build_agent_workflow(state, emulator)
                await workflow.execute()
                state = await workflow.get_state()
                if state.iteration % ITERATIONS_PER_BACKUP == 0:
                    await create_backup(state, emulator)
        except Exception:  # noqa: BLE001
            logger.exception("Agent workflow raised an exception.")
            await create_backup(state, emulator)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom-path", type=str, required=True)
    parser.add_argument("--backup-folder", type=Path, required=False)
    parser.add_argument("--mute-sound", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.rom_path, args.mute_sound, args.backup_folder))
