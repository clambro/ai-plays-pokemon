from contextlib import AbstractAsyncContextManager
from pathlib import Path

import aiofiles
from aiohttp import web
from aiohttp.web import Request, Response
from loguru import logger

from agent.state import AgentState
from emulator.game_state import YellowLegacyGameState
from streaming.schemas import GameStateView


class BackgroundStreamServer(AbstractAsyncContextManager):
    """Async context manager for hosting the background HTML page with live updates."""

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

        logger.info(f"Background server started at http://{self.host}:{self.port}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Stop the web server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
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

    async def update(self, agent_state: AgentState, game_state: YellowLegacyGameState) -> None:
        """Update the current state data."""
        self._current_data = await GameStateView.from_states(agent_state, game_state)
