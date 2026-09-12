"""Preview the streaming background with fixture data.

This development script starts the server briefly to inspect styles and layouts.
"""

import asyncio

from streaming.preview_data import MOCK_DATA
from streaming.server import BackgroundStreamServer


async def main() -> None:
    """Run the server with mock data for a few seconds."""
    async with BackgroundStreamServer() as server:
        server._current_data = MOCK_DATA.model_copy(  # noqa: SLF001
            update={"total_tokens": 12_345_678},
        )
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
