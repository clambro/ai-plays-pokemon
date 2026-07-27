"""Backup and restore operations for persistent game data."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import aiofiles
import aiofiles.os
from loguru import logger

from agent.state import AgentState
from common.constants import BACKUP_AGENT_STATE_NAME, DB_FILE_PATH, DB_FOLDER_NAME, OUTPUTS_FOLDER

OUTPUT_PREFIX = "agent_"
BACKUP_PREFIX = "backup_"


def get_output_folder() -> Path:
    """Get the output folder for the current run."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return OUTPUTS_FOLDER / f"{OUTPUT_PREFIX}{timestamp}"


async def create_backup(agent_state: AgentState) -> None:
    """Save agent state and the current database into a timestamped backup.

    Args:
        agent_state: State to serialize, including the output folder and emulator save state.
    """
    logger.info(f"Creating backup at iteration {agent_state.iteration}.")

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_folder = agent_state.folder / f"{BACKUP_PREFIX}{timestamp}_iter_{agent_state.iteration}"
    await aiofiles.os.makedirs(backup_folder, exist_ok=True)

    backup_db_folder = backup_folder / DB_FOLDER_NAME
    await aiofiles.os.makedirs(backup_db_folder, exist_ok=True)

    async with aiofiles.open(backup_folder / BACKUP_AGENT_STATE_NAME, "w") as f:
        await f.write(agent_state.model_dump_json())

    await _copy_dir_async(src=DB_FILE_PATH.parent, dst=backup_db_folder)


async def load_backup(backup_folder: Path) -> AgentState:
    """Restore agent state and replace the active database from a backup.

    Args:
        backup_folder: Backup containing serialized agent state and a database directory.

    Returns:
        The restored agent state.
    """
    async with aiofiles.open(backup_folder / BACKUP_AGENT_STATE_NAME) as f:
        agent_state = AgentState.model_validate_json(await f.read())

    backup_db_folder = backup_folder / DB_FOLDER_NAME
    await _copy_dir_async(src=backup_db_folder, dst=DB_FILE_PATH.parent)

    return agent_state


async def load_latest_backup() -> AgentState:
    """Restore the newest timestamped backup.

    Returns:
        Agent state loaded from the newest backup under the newest output directory.

    Raises:
        ValueError: No output directory or backup exists.
    """
    subfolders = []
    for name in await aiofiles.os.listdir(OUTPUTS_FOLDER):
        folder = OUTPUTS_FOLDER / name
        if name.startswith(OUTPUT_PREFIX) and await aiofiles.os.path.isdir(folder):
            subfolders.append(folder)
    latest_subfolder = max(subfolders, key=lambda f: f.name)
    backups = []
    for name in await aiofiles.os.listdir(latest_subfolder):
        folder = latest_subfolder / name
        if name.startswith(BACKUP_PREFIX) and await aiofiles.os.path.isdir(folder):
            backups.append(folder)
    latest_backup = max(backups, key=lambda f: f.name)
    return await load_backup(latest_backup)


async def _copy_dir_async(src: Path, dst: Path) -> None:
    """Copy the files directly inside one directory to another.

    Args:
        src: Source directory whose files should be copied.
        dst: Destination directory to create and populate.
    """
    await aiofiles.os.makedirs(dst, exist_ok=True)

    async def copy_file(src_file: Path, dst_file: Path) -> None:
        """Copy one file asynchronously.

        Args:
            src_file: Existing file to read.
            dst_file: Destination file to overwrite.
        """
        async with aiofiles.open(src_file, "rb") as src_f, aiofiles.open(dst_file, "wb") as dst_f:
            await dst_f.write(await src_f.read())

    entries = await aiofiles.os.scandir(src)
    files = [Path(entry.path) for entry in entries if entry.is_file()]

    tasks = []
    for src_file in files:
        dst_file = dst / src_file.name
        tasks.append(copy_file(src_file, dst_file))

    await asyncio.gather(*tasks)
