"""HTTP server for the live game-state display."""

import asyncio
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import TYPE_CHECKING, Self

from aiohttp import WSCloseCode, WSMsgType, web
from loguru import logger

from streaming.schemas import GameStateView

if TYPE_CHECKING:
    from aiohttp.web import FileResponse, Request, Response

    from agent.state import AgentState
    from emulator.emulator import Emulator
    from emulator.game_state import GameState


class BackgroundStreamServer(AbstractAsyncContextManager):
    """Async context manager for hosting the background HTML page with live updates."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        *,
        emulator: Emulator | None = None,
    ) -> None:
        """Initialize the background stream server."""
        self.host = host
        self.port = port
        self.emulator = emulator
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self._game_state: GameState | None = None
        self._agent_state: AgentState | None = None
        self._frame_sockets: set[web.WebSocketResponse] = set()
        self._background_dir = Path("streaming/background")

        self.app.on_shutdown.append(self._close_frame_sockets)
        self.app.router.add_get("/", self._serve_index)
        self.app.router.add_get("/api/state.json", self._serve_state)
        self.app.router.add_get("/api/frames", self._serve_frames)
        self.app.router.add_get("/style.css", self._serve_css)
        self.app.router.add_get("/script.js", self._serve_js)
        self.app.router.add_static("/assets", self._background_dir / "assets")

    async def __aenter__(self) -> Self:
        """Start the web server."""
        self.runner = web.AppRunner(self.app)
        try:
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
        except BaseException:
            try:
                await self.runner.cleanup()
            finally:
                self.site = None
                self.runner = None
            raise

        logger.info(f"Background server started at http://{self.host}:{self.port}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Stop the web server."""
        try:
            if self.site:
                await self.site.stop()
        finally:
            try:
                if self.runner:
                    await self.runner.cleanup()
            finally:
                self.site = None
                self.runner = None

        logger.info("Background server stopped")

    async def _serve_index(self, request: Request) -> FileResponse:  # noqa: ARG002
        """Serve the main HTML page."""
        return web.FileResponse(
            self._background_dir / "index.html",
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

    async def _serve_css(self, request: Request) -> FileResponse:  # noqa: ARG002
        """Serve the CSS file."""
        return web.FileResponse(
            self._background_dir / "style.css",
            headers={"Content-Type": "text/css; charset=utf-8"},
        )

    async def _serve_js(self, request: Request) -> FileResponse:  # noqa: ARG002
        """Serve the JavaScript file."""
        return web.FileResponse(
            self._background_dir / "script.js",
            headers={"Content-Type": "application/javascript; charset=utf-8"},
        )

    async def _serve_state(self, request: Request) -> Response:  # noqa: ARG002
        """Serve the current state data as JSON."""
        if self._agent_state is None or self._game_state is None:
            return web.json_response(None)
        data = GameStateView.from_states(self._agent_state, self._game_state)
        return web.json_response(data.model_dump(mode="json"))

    async def _serve_frames(self, request: Request) -> web.WebSocketResponse:
        """Stream the latest emulator frame to a browser canvas."""
        if self.emulator is None:
            raise web.HTTPServiceUnavailable
        socket = web.WebSocketResponse()
        await socket.prepare(request)
        self._frame_sockets.add(socket)
        try:
            while not socket.closed:
                await socket.send_bytes(await self.emulator.get_frame_bytes())
                try:
                    message = await socket.receive(timeout=1 / 30)
                except TimeoutError:
                    continue
                if message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                    break
        except ConnectionResetError:
            pass
        finally:
            self._frame_sockets.discard(socket)
            await socket.close()
        return socket

    async def _close_frame_sockets(self, app: web.Application) -> None:  # noqa: ARG002
        """Close active video connections before waiting for request handlers to finish."""
        await asyncio.gather(
            *(socket.close(code=WSCloseCode.GOING_AWAY) for socket in tuple(self._frame_sockets))
        )

    def update_data(self, agent_state: AgentState, game_state: GameState) -> None:
        """Capture safe game data and retain the live agent state for browser polls."""
        self._agent_state = agent_state
        self._game_state = game_state
