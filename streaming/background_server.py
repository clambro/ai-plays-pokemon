from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any

import aiofiles
from aiohttp import web
from aiohttp.web import Request, Response
from loguru import logger

MOCK_DATA = {
    "iteration": 15247,
    "money": 18143,
    "pokedex_seen": 45,
    "pokedex_caught": 21,
    "total_cost": 23.51,
    "play_time_seconds": 596153,  # about 165 hours
    "badges": ["BOULDERBADGE", "CASCADEBADGE", "THUNDERBADGE"],
    "party": [
        {
            "name": "ECHO",
            "species": "Golbat",
            "type1": "POISON",
            "type2": "FLYING",
            "level": 22,
            "hp": 0,
            "max_hp": 70,
            "moves": ["Wing Attack", "Confuse Ray", "Bite", "Haze"],
        },
        {
            "name": "CRAG",
            "species": "Geodude",
            "type1": "ROCK",
            "type2": "GROUND",
            "level": 18,
            "hp": 45,
            "max_hp": 45,
            "moves": ["Tackle", "Defense Curl", "Rock Throw", "Self-Destruct"],
        },
        {
            "name": "PULSAR",
            "species": "Magnemite",
            "type1": "ELECTRIC",
            "level": 18,
            "hp": 0,
            "max_hp": 36,
            "moves": ["Tackle", "Sonic Boom", "Thunder Shock", "Supersonic"],
        },
        {
            "name": "SPARKY",
            "species": "Pikachu",
            "type1": "ELECTRIC",
            "level": 24,
            "hp": 68,
            "max_hp": 68,
            "status": "POISONED",
            "moves": ["Thunder Shock", "Growl", "Thunder Wave", "Quick Attack"],
        },
        {
            "name": "SUBTERRA",
            "species": "Diglett",
            "type1": "GROUND",
            "level": 18,
            "hp": 18,
            "max_hp": 52,
            "moves": ["Scratch", "Growl"],
        },
    ],
    "goals": [
        "Travel through Rock Tunnel to reach Lavender Town.",
        "Obtain HM05 (Flash).",
        "Acquire a drink for the Saffron City guard.",
    ],
    "log": [
        {
            "iteration": 15246,
            "thought": "Ugh, a random battle. My path traversal was interrupted. I'm facing a wild Diglett. My goal is to get out of here, not to battle. ECHO is a higher level, so I should be able to run away successfully. I'll use the select_battle_option tool to select RUN.",  # noqa: E501
        },
        {
            "iteration": 15247,
            "thought": "Oh, come on! Just when I was making good time. Another Diglett... alright, let's just get out of here. No time for battles right now!",  # noqa: E501
        },
    ],
}


class BackgroundStreamServer(AbstractAsyncContextManager):
    """Async context manager for hosting the background HTML page with live updates."""

    def __init__(self, host: str = "localhost", port: int = 8080) -> None:
        """Initialize the background stream server."""
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self._current_data: dict[str, Any] = {}
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
        return web.json_response(self._current_data)

    async def update(self, data: dict[str, Any]) -> None:
        """Update the current state data."""
        self._current_data = data  # TODO: Make this a schema.
