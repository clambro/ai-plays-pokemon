"""HTTP state, static assets, and video streaming integration tests."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientSession, WSMsgType
from aiohttp.web import HTTPOk

import streaming.server as server_module
from agent.state import AgentState
from emulator.game_state import GameState
from emulator.parsers.pokemon import _INT_TO_SPECIES_MAP
from streaming.server import BackgroundStreamServer


@pytest.mark.integration
async def test_html_page_assets_are_served() -> None:
    """Serve the HTML, JavaScript, and CSS with their expected content types."""
    async with BackgroundStreamServer(host="localhost", port=8081), ClientSession() as session:
        async with session.get("http://localhost:8081/") as response:
            assert response.status == HTTPOk.status_code
            assert response.content_type == "text/html"

        async with session.get("http://localhost:8081/style.css") as response:
            assert response.status == HTTPOk.status_code
            assert response.content_type == "text/css"

        async with session.get("http://localhost:8081/script.js") as response:
            assert response.status == HTTPOk.status_code
            assert response.content_type == "application/javascript"


@pytest.mark.integration
async def test_html_page_handles_empty_data() -> None:
    """Test that the HTML page handles empty/missing data gracefully."""
    async with BackgroundStreamServer(host="localhost", port=8082), ClientSession() as session:
        async with session.get("http://localhost:8082/") as response:
            assert response.status == HTTPOk.status_code

        async with session.get("http://localhost:8082/api/state.json") as response:
            assert response.status == HTTPOk.status_code
            assert await response.json() is None


@pytest.mark.integration
def test_html_page_assets_exist() -> None:
    """Test that all required asset files exist and are accessible."""
    background_dir = Path("streaming/background")

    assert (background_dir / "index.html").exists()
    assert (background_dir / "style.css").exists()
    assert (background_dir / "script.js").exists()

    assets_dir = background_dir / "assets"
    assert assets_dir.exists()

    badges_dir = assets_dir / "badges"
    assert badges_dir.exists()

    expected_badges = ["boulderbadge.png", "cascadebadge.png", "thunderbadge.png"]
    for badge in expected_badges:
        assert (badges_dir / badge).exists(), f"Badge asset {badge} not found."

    pokemon_dir = assets_dir / "pokemon"
    assert pokemon_dir.exists()

    expected_pokemon = {
        f"{species.lower().replace(' ', '').replace('♀', 'f').replace('♂', 'm')}.png"
        for species in _INT_TO_SPECIES_MAP.values()
        if species != "GHOST"
    }
    installed_pokemon = {path.name for path in pokemon_dir.glob("*.png")}
    assert installed_pokemon == expected_pokemon


@pytest.mark.integration
async def test_commentary_updates_without_a_new_game_snapshot(tmp_path: Path) -> None:
    """Publish fresh commentary while retaining the last safe game data."""
    state = AgentState(folder=tmp_path)
    game_state = Mock(spec=GameState)
    game_state.party = []
    game_state.player = Mock(
        money=100,
        pokedex_seen=1,
        pokedex_caught=[],
        play_time_seconds=20,
        badges=[],
    )
    async with (
        BackgroundStreamServer(host="localhost", port=8083) as server,
        ClientSession() as session,
    ):
        server.update_data(state, game_state)

        async with session.get("http://localhost:8083/api/state.json") as response:
            assert response.status == HTTPOk.status_code
            initial = await response.json()

        state.public_log.add(1, "Continue exploring.")
        # The emulator has not supplied another safe snapshot yet.
        async with session.get("http://localhost:8083/api/state.json") as response:
            assert await response.json() == {
                **initial,
                "log": [{"iteration": 1, "thought": "Continue exploring."}],
            }


@pytest.mark.integration
async def test_game_frames_stream_over_websocket() -> None:
    """The browser receives a raw RGBA game frame over a persistent connection."""
    frame = bytes([0, 80, 160, 255]) * (160 * 144)
    emulator = Mock()
    emulator.get_frame_bytes = AsyncMock(return_value=frame)

    async with asyncio.timeout(3), ClientSession() as session:
        async with BackgroundStreamServer(host="localhost", port=8085, emulator=emulator):
            socket = await session.ws_connect("http://localhost:8085/api/frames")
            message = await socket.receive()
            assert message.type is WSMsgType.BINARY
            assert message.data == frame

            async def receive_until_closed() -> None:
                async for message in socket:
                    assert message.type is WSMsgType.BINARY
                    assert message.data == frame

            receiver = asyncio.create_task(receive_until_closed())

        await receiver
        assert socket.closed


@pytest.mark.integration
async def test_server_cleans_up_if_startup_is_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clean up the partially initialized runner when server startup is cancelled."""
    startup_started = asyncio.Event()
    keep_starting = asyncio.Event()

    async def wait_to_start(_site: server_module.web.TCPSite) -> None:
        startup_started.set()
        await keep_starting.wait()

    monkeypatch.setattr(server_module.web.TCPSite, "start", wait_to_start)
    server = BackgroundStreamServer(host="localhost", port=8084)
    startup = asyncio.create_task(server.__aenter__())
    await startup_started.wait()

    startup.cancel()

    with pytest.raises(asyncio.CancelledError):
        await startup
    assert server.runner is None
    assert server.site is None
