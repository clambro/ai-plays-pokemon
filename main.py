import argparse
import asyncio
from loguru import logger
from pathlib import Path
from agent.app import build_agent_application
from emulator.emulator import YellowLegacyEmulator


async def main(
    rom_path: str,
    memory_dir: str,
    backup_dir: str,
    state_path: str | None = None,
) -> None:
    """
    Get the emulator ticking on an async thread, and iteratively run the agent.

    :param rom_path: The path to the ROM file.
    :param state_path: Optional path to load a saved state from.
    """
    async with YellowLegacyEmulator(rom_path, state_path) as emulator:
        agent_app = build_agent_application(Path(memory_dir), Path(backup_dir), emulator)
        try:
            await agent_app.arun()
        except Exception:  # noqa: BLE001
            logger.exception("Agent app raised an exception.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom-path", type=str, required=True)
    parser.add_argument("--memory-dir", type=str, required=True)
    parser.add_argument("--backup-dir", type=str, required=True)
    parser.add_argument("--state-path", type=str, required=False)
    args = parser.parse_args()
    asyncio.run(main(args.rom_path, args.memory_dir, args.backup_dir, args.state_path))
