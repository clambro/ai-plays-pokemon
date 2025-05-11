import argparse
import asyncio
from datetime import datetime
from loguru import logger
from pathlib import Path
from agent.app import build_agent_workflow
from agent.state import AgentState
from common.constants import MAP_SUBFOLDER, SPRITE_SUBFOLDER, WARP_SUBFOLDER
from emulator.emulator import YellowLegacyEmulator
import aiofiles
import aiofiles.os


async def main(
    rom_path: str,
    parent_folder: str,
    mute_sound: bool,
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
    await aiofiles.os.makedirs(folder / SPRITE_SUBFOLDER, exist_ok=True)
    await aiofiles.os.makedirs(folder / WARP_SUBFOLDER, exist_ok=True)

    async with YellowLegacyEmulator(rom_path, state_path, mute_sound=mute_sound) as emulator:
        state = AgentState(folder=folder)
        try:
            while True:
                workflow = build_agent_workflow(state, emulator)
                await workflow.execute()
                state = await workflow.get_state()
        except Exception:  # noqa: BLE001
            logger.exception("Agent workflow raised an exception.")
            async with aiofiles.open("notes/agent_state.json", "w") as f:
                await f.write(state.model_dump_json())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom-path", type=str, required=True)
    parser.add_argument("--parent-folder", type=str, required=True)
    parser.add_argument("--state-path", type=str, required=False)
    parser.add_argument("--mute-sound", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.rom_path, args.parent_folder, args.mute_sound, args.state_path))
