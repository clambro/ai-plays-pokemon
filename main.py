import argparse
import asyncio
from datetime import datetime
from loguru import logger
from pathlib import Path
from agent.app import build_agent_application
from agent.state import AgentState
from common.constants import MAP_SUBFOLDER
from emulator.emulator import YellowLegacyEmulator
import aiofiles
import aiofiles.os


async def main(
    rom_path: str,
    parent_folder: str,
    state_path: str | None = None,
) -> None:
    """
    Get the emulator ticking on an async thread, and iteratively run the agent.

    :param rom_path: The path to the ROM file.
    :param state_path: Optional path to load a saved state from.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(parent_folder) / timestamp
    await aiofiles.os.makedirs(folder, exist_ok=True)
    await aiofiles.os.makedirs(folder / MAP_SUBFOLDER, exist_ok=True)

    async with YellowLegacyEmulator(rom_path, state_path) as emulator:
        agent_app = build_agent_application(folder, emulator)
        try:
            await agent_app.arun()
        except Exception:  # noqa: BLE001
            logger.exception("Agent app raised an exception.")
            state = AgentState.model_validate(agent_app.state)
            async with aiofiles.open("notes/agent_state.json", "w") as f:
                await f.write(state.model_dump_json())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom-path", type=str, required=True)
    parser.add_argument("--parent-folder", type=str, required=True)
    parser.add_argument("--state-path", type=str, required=False)
    args = parser.parse_args()
    asyncio.run(main(args.rom_path, args.parent_folder, args.state_path))
