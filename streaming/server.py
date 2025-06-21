from contextlib import AbstractAsyncContextManager
from pathlib import Path

import aiofiles
from aiohttp import web
from aiohttp.web import Request, Response
from loguru import logger

from agent.state import AgentState
from emulator.game_state import YellowLegacyGameState
from memory.raw_memory import RawMemory
from streaming.schemas import GameStateView, LogEntryView


class BackgroundStreamServer(AbstractAsyncContextManager):
    """Async context manager for hosting the background HTML page with live updates."""

    # Global instance for dependency injection
    _instance: "BackgroundStreamServer | None" = None

    @classmethod
    def get_instance(cls) -> "BackgroundStreamServer | None":
        """Get the global instance of the stream server."""
        return cls._instance

    @classmethod
    def _set_instance(cls, instance: "BackgroundStreamServer | None") -> None:
        """Set the global instance of the stream server."""
        cls._instance = instance

    def __init__(self, host: str = "localhost", port: int = 8080) -> None:
        """Initialize the background stream server."""
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self._current_data: GameStateView | None = None
        self._background_dir = Path("streaming/background")

        self.app.router.add_get("/", self._serve_index)
        self.app.router.add_get("/api/state.json", self._serve_state)
        self.app.router.add_get("/style.css", self._serve_css)
        self.app.router.add_get("/script.js", self._serve_js)
        self.app.router.add_static("/assets", self._background_dir / "assets")

    async def __aenter__(self) -> "BackgroundStreamServer":
        """Start the web server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        self._set_instance(self)

        logger.info(f"Background server started at http://{self.host}:{self.port}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Stop the web server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

        self._set_instance(None)

        logger.info("Background server stopped")

    async def _serve_index(self, request: Request) -> Response:  # noqa: ARG002
        """Serve the main HTML page."""
        index_path = self._background_dir / "index.html"
        async with aiofiles.open(index_path) as f:
            content = await f.read()
        return web.Response(text=content, content_type="text/html")

    async def _serve_css(self, request: Request) -> Response:  # noqa: ARG002
        """Serve the CSS file."""
        css_path = self._background_dir / "style.css"
        async with aiofiles.open(css_path) as f:
            content = await f.read()
        return web.Response(text=content, content_type="text/css")

    async def _serve_js(self, request: Request) -> Response:  # noqa: ARG002
        """Serve the JavaScript file."""
        js_path = self._background_dir / "script.js"
        async with aiofiles.open(js_path) as f:
            content = await f.read()
        return web.Response(text=content, content_type="application/javascript")

    async def _serve_state(self, request: Request) -> Response:  # noqa: ARG002
        """Serve the current state data as JSON."""
        if self._current_data is None:
            return web.Response()
        return web.json_response(self._current_data.model_dump(mode="json"))

    def update_log(self, memory: RawMemory) -> None:
        """Update the current log data."""
        if self._current_data is not None:
            self._current_data.log = LogEntryView.from_memory(memory)
        else:
            logger.warning("Current data is not set. Cannot update log")

    async def update_data(self, agent_state: AgentState, game_state: YellowLegacyGameState) -> None:
        """Update the current state data."""
        self._current_data = await GameStateView.from_states(agent_state, game_state)


def update_background_log_from_memory(memory: RawMemory) -> None:
    """Update the background log from the memory."""
    server = BackgroundStreamServer.get_instance()
    if server is not None:
        server.update_log(memory)
    else:
        logger.warning("Stream server not available for update")


async def update_background_from_states(
    agent_state: AgentState,
    game_state: YellowLegacyGameState,
) -> None:
    """Helper function to update the stream server from anywhere in the codebase."""
    server = BackgroundStreamServer.get_instance()
    if server is not None:
        await server.update_data(agent_state, game_state)
    else:
        logger.warning("Stream server not available for update")
