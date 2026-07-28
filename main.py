"""Launch the Pokémon-playing agent application."""

import argparse
import asyncio
from pathlib import Path

import aiofiles
import aiofiles.os
from loguru import logger

from agent.app import run_agent_workflow
from agent.state import AgentState
from common.backup_service import create_backup, get_output_folder, load_backup, load_latest_backup
from common.constants import BACKUP_INTERVAL_SECONDS, DEFAULT_ROM_PATH
from common.telemetry import setup_telemetry
from database.db_config import init_fresh_db
from emulator.emulator import YellowLegacyEmulator
from streaming.server import BackgroundStreamServer


async def main(
    rom_path: Path,
    backup_folder: Path | None = None,
    *,
    mute_sound: bool = True,
    load_latest: bool = False,
) -> None:
    """Run the emulator, streaming server, and iterative agent workflow.

    Args:
        rom_path: ROM file to load.
        backup_folder: Specific backup to restore before starting.
        mute_sound: Whether to initialize the emulator with zero volume.
        load_latest: Whether to restore the newest available backup.

    Raises:
        ValueError: Both ``backup_folder`` and ``load_latest`` are specified.
    """
    if backup_folder and load_latest:
        raise ValueError("Cannot load latest backup and specify a backup folder at the same time.")

    setup_telemetry()

    folder = get_output_folder()

    if backup_folder:
        state = await load_backup(backup_folder)
        emulator_state = state.emulator_save_state
    elif load_latest:
        state = await load_latest_backup()
        emulator_state = state.emulator_save_state
    else:
        await init_fresh_db()
        state = AgentState(folder=folder)
        emulator_state = None

    state.folder = folder
    state.emulator_save_state = None
    await aiofiles.os.makedirs(folder)

    async with (
        YellowLegacyEmulator(str(rom_path), emulator_state, mute_sound=mute_sound) as emulator,
        BackgroundStreamServer() as stream_server,
    ):
        stream_server.update_data(state, await emulator.get_game_state())  # Initialize the view.
        if not emulator_state:
            await asyncio.sleep(30)  # Some time to manually get to the new game screen.
        loop = asyncio.get_running_loop()
        next_backup_at = loop.time() + BACKUP_INTERVAL_SECONDS
        try:
            while True:
                state = await run_agent_workflow(state, emulator)
                if loop.time() >= next_backup_at:
                    emulator_save_state = await emulator.get_emulator_save_state()
                    await create_backup(state, emulator_save_state)
                    next_backup_at = loop.time() + BACKUP_INTERVAL_SECONDS
        except Exception:  # noqa: BLE001
            logger.exception("Agent workflow raised an exception.")
            emulator_save_state = await emulator.get_emulator_save_state()
            await create_backup(state, emulator_save_state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom-path", type=Path, required=False, default=Path(DEFAULT_ROM_PATH))
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
