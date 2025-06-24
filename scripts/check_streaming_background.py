"""
Hacky script to shove some dummy data from the tests into the background server and spin it up so
that I can quickly visualize styles and layouts.
"""

import asyncio

from streaming.server import BackgroundStreamServer
from streaming.tests.integration.test_server import MOCK_DATA


async def main() -> None:
    """Run the server with mock data for a few seconds."""
    async with BackgroundStreamServer() as server:
        server._current_data = MOCK_DATA  # noqa: SLF001
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
