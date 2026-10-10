"""Launch the Pokémon-playing agent application."""

import argparse
import asyncio
from contextlib import suppress
from pathlib import Path

import aiofiles
import aiofiles.os
from loguru import logger

from agent.app import dispatch_agent
from agent.context import AgentContext
from agent.state import AgentState
from backup import create_backup, get_output_folder, load_backup, load_latest_backup
from common.constants import BACKUP_INTERVAL_SECONDS, DEFAULT_ROM_PATH
from common.telemetry import setup_telemetry
from database.db_config import init_fresh_db
from emulator.emulator import Emulator
from streaming.server import BackgroundStreamServer


async def main(
    rom_path: Path,
    backup_folder: Path | None = None,
    *,
    mute_sound: bool = True,
    load_latest: bool = False,
) -> None:
    """Run the emulator, streaming server, and agent application.

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
        Emulator(str(rom_path), emulator_state, mute_sound=mute_sound) as emulator,
        BackgroundStreamServer(emulator=emulator) as stream_server,
    ):
        context = AgentContext(state=state, emulator=emulator)
        stream_server.update_data(context.state, await emulator.get_game_state())
        stream_refresh_task = asyncio.create_task(
            _refresh_stream(stream_server, context.state, emulator)
        )
        try:
            loop = asyncio.get_running_loop()
            next_backup_at = loop.time() + BACKUP_INTERVAL_SECONDS
            while True:
                await dispatch_agent(context)
                if loop.time() >= next_backup_at:
                    emulator_save_state = await emulator.get_emulator_save_state()
                    await create_backup(context.state, emulator_save_state)
                    next_backup_at = loop.time() + BACKUP_INTERVAL_SECONDS
        except Exception:  # noqa: BLE001
            logger.exception("Agent application raised an exception.")
            emulator_save_state = await emulator.get_emulator_save_state()
            await create_backup(context.state, emulator_save_state)
        finally:
            stream_refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await stream_refresh_task


async def _refresh_stream(
    server: BackgroundStreamServer,
    state: AgentState,
    emulator: Emulator,
) -> None:
    """Refresh the stream's game snapshot independently of gameplay decisions."""
    while True:
        await asyncio.sleep(0.5)
        try:
            server.update_data(state, await emulator.get_game_state())
        except Exception:  # noqa: BLE001
            logger.exception("Background stream refresh failed.")


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
