"""Preview the streaming background with fixture data.

This development script starts the server briefly to inspect styles and layouts.
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
