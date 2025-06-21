import asyncio
from datetime import UTC, datetime
from pathlib import Path

import aiofiles
from loguru import logger

from agent.state import AgentState
from common.constants import BACKUP_AGENT_STATE_NAME, DB_FILE_PATH, DB_FOLDER_NAME, OUTPUTS_FOLDER

OUTPUT_PREFIX = "agent_"
BACKUP_PREFIX = "backup_"


async def get_output_folder() -> Path:
    """Get the output folder for the current run."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return OUTPUTS_FOLDER / f"{OUTPUT_PREFIX}{timestamp}"


async def create_backup(agent_state: AgentState) -> None:
    """Save the current game state, agent state, and database to a backup folder."""
    logger.info(f"Creating backup at iteration {agent_state.iteration}.")

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_folder = agent_state.folder / f"{BACKUP_PREFIX}{timestamp}_iter_{agent_state.iteration}"
    backup_folder.mkdir(parents=True, exist_ok=True)

    backup_db_folder = backup_folder / DB_FOLDER_NAME
    backup_db_folder.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(backup_folder / BACKUP_AGENT_STATE_NAME, "w") as f:
        await f.write(agent_state.model_dump_json())

    await _copy_dir_async(src=DB_FILE_PATH.parent, dst=backup_db_folder)


async def load_backup(backup_folder: Path) -> AgentState:
    """Load the agent state from a backup folder and set the current DB to the backup DB."""
    async with aiofiles.open(backup_folder / BACKUP_AGENT_STATE_NAME) as f:
        agent_state = AgentState.model_validate_json(await f.read())

    backup_db_folder = backup_folder / DB_FOLDER_NAME
    await _copy_dir_async(src=backup_db_folder, dst=DB_FILE_PATH.parent)

    return agent_state


async def load_latest_backup() -> AgentState:
    """Load the latest backup from the backups folder."""
    subfolders = [
        f for f in OUTPUTS_FOLDER.iterdir() if f.is_dir() and f.name.startswith(OUTPUT_PREFIX)
    ]
    latest_subfolder = max(subfolders, key=lambda f: f.name)
    backups = [
        f for f in latest_subfolder.iterdir() if f.is_dir() and f.name.startswith(BACKUP_PREFIX)
    ]
    latest_backup = max(backups, key=lambda f: f.name)
    return await load_backup(latest_backup)


async def _copy_dir_async(src: Path, dst: Path) -> None:
    """Asynchronously copy a directory and its contents."""
    dst.mkdir(parents=True, exist_ok=True)

    async def copy_file(src_file: Path, dst_file: Path) -> None:
        async with aiofiles.open(src_file, "rb") as src_f, aiofiles.open(dst_file, "wb") as dst_f:
            await dst_f.write(await src_f.read())

    files = [f for f in src.iterdir() if f.is_file()]

    tasks = []
    for src_file in files:
        dst_file = dst / src_file.name
        tasks.append(copy_file(src_file, dst_file))

    await asyncio.gather(*tasks)
