from datetime import datetime

import aiofiles
from loguru import logger

from agent.state import AgentState
from common.constants import BACKUP_AGENT_STATE_NAME, DB_FILE_PATH, DB_FILENAME
from emulator.emulator import YellowLegacyEmulator


async def create_backup(agent_state: AgentState, emulator: YellowLegacyEmulator) -> None:
    """Save the current game state, agent state, and database to a backup folder."""
    logger.info(f"Creating backup at iteration {agent_state.iteration}.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = agent_state.folder / f"backup_{timestamp}_iter_{agent_state.iteration}"
    backup_folder.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(backup_folder / BACKUP_AGENT_STATE_NAME, "w") as f:
        await f.write(agent_state.model_dump_json())

    async with aiofiles.open(DB_FILE_PATH, "rb") as current_db_path:
        async with aiofiles.open(backup_folder / DB_FILENAME, "wb") as backup_db_path:
            content = await current_db_path.read()
            await backup_db_path.write(content)
