import argparse
import asyncio
from datetime import datetime

import aiofiles
import aiofiles.os
from loguru import logger

from agent.app import build_agent_workflow
from agent.state import AgentState
from backup.service import create_backup
from common.constants import ITERATIONS_PER_BACKUP, OUTPUTS_FOLDER
from database.db_config import init_fresh_db
from emulator.emulator import YellowLegacyEmulator


async def main(
    rom_path: str,
    mute_sound: bool,
    state_path: str | None = None,
) -> None:
    """
    Get the emulator ticking on an async thread, and iteratively run the agent.

    :param rom_path: The path to the ROM file.
    :param state_path: Optional path to load a saved state from.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUTPUTS_FOLDER / timestamp
    await aiofiles.os.makedirs(folder, exist_ok=True)
    await init_fresh_db()

    async with YellowLegacyEmulator(rom_path, state_path, mute_sound=mute_sound) as emulator:
        state = AgentState(folder=folder)
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
    parser.add_argument("--state-path", type=str, required=False)
    parser.add_argument("--mute-sound", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.rom_path, args.mute_sound, args.state_path))
