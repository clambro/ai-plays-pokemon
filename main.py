import argparse
import asyncio

from emulator.context import EmulatorContext


async def main(rom_path: str, state_path: str | None = None) -> None:
    """
    Get the emulator ticking on an async thread, and iteratively run the agent.

    :param rom_path: The path to the ROM file.
    :param state_path: Optional path to load a saved state from.
    """
    async with EmulatorContext(rom_path, state_path):
        await asyncio.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom-path", type=str, required=True)
    parser.add_argument("--state-path", type=str, required=False)
    args = parser.parse_args()
    asyncio.run(main(args.rom_path, args.state_path))
