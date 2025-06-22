import argparse
import asyncio
from pathlib import Path

import aiofiles
import aiofiles.os
from loguru import logger

from agent.app import build_agent_workflow
from agent.state import AgentState
from common.backup_service import create_backup, get_output_folder, load_backup, load_latest_backup
from common.constants import DEFAULT_ROM_PATH, ITERATIONS_PER_BACKUP
from database.db_config import init_fresh_db
from emulator.emulator import YellowLegacyEmulator
from streaming.server import BackgroundStreamServer


async def main(
    rom_path: Path = Path(DEFAULT_ROM_PATH),
    backup_folder: Path | None = None,
    *,
    mute_sound: bool = True,
    load_latest: bool = False,
) -> None:
    """
    Get the emulator ticking on an async thread, and iteratively run the agent.

    :param rom_path: The path to the ROM file.
    :param backup_folder: Optional path to load a saved state from.
    :param mute_sound: Whether to mute the sound.
    :param load_latest: Whether to load the latest backup.
    """
    if backup_folder and load_latest:
        raise ValueError("Cannot load latest backup and specify a backup folder at the same time.")

    folder = await get_output_folder()

    if backup_folder:
        state = await load_backup(backup_folder)
        state.folder = folder
        emulator_state = state.emulator_save_state
    elif load_latest:
        state = await load_latest_backup()
        state.folder = folder
        emulator_state = state.emulator_save_state
    else:
        await init_fresh_db()
        state = AgentState(folder=folder)
        emulator_state = None

    await aiofiles.os.makedirs(folder)

    async with (
        YellowLegacyEmulator(str(rom_path), emulator_state, mute_sound=mute_sound) as emulator,
        BackgroundStreamServer() as stream_server,
    ):
        await stream_server.update_data(state, emulator.get_game_state())  # Initialize the view.
        if not emulator_state:
            await asyncio.sleep(30)  # Some time to manually get to the new game screen.
        try:
            while True:
                workflow = build_agent_workflow(state, emulator)
                await workflow.execute()
                state = await workflow.get_state()
                if state.iteration % ITERATIONS_PER_BACKUP == 0:
                    await create_backup(state)
        except Exception:  # noqa: BLE001
            logger.exception("Agent workflow raised an exception.")
            await create_backup(state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom-path", type=Path, required=False)
    parser.add_argument("--backup-folder", type=Path, required=False)
    parser.add_argument("--mute-sound", action="store_true")
    parser.add_argument("--load-latest", action="store_true")
    args = parser.parse_args()
    asyncio.run(
        main(
            rom_path=args.rom_path,
            backup_folder=args.backup_folder,
            mute_sound=args.mute_sound,
            load_latest=args.load_latest,
        )
    )
