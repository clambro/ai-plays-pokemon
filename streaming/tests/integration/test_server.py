"""Tests for the streaming background HTML page.

These tests validate that the HTML page renders correctly without console errors
and that all JavaScript functionality works as expected.
"""

import asyncio
from pathlib import Path

import pytest
from aiohttp import ClientSession
from aiohttp.web import HTTPOk

import streaming.server as server_module
from emulator.parsers.pokemon import _INT_TO_SPECIES_MAP
from streaming.preview_data import MOCK_DATA
from streaming.server import BackgroundStreamServer


@pytest.mark.integration
async def test_html_page_renders_without_errors() -> None:
    """Test that the HTML, JS, and CSS files load correctly, and that the API returns valid JSON."""
    async with BackgroundStreamServer(host="localhost", port=8081) as server:
        server._current_data = MOCK_DATA

        async with ClientSession() as session:
            async with session.get("http://localhost:8081/") as response:
                assert response.status == HTTPOk.status_code
                assert response.content_type == "text/html"

            async with session.get("http://localhost:8081/style.css") as response:
                assert response.status == HTTPOk.status_code
                assert response.content_type == "text/css"

            async with session.get("http://localhost:8081/script.js") as response:
                assert response.status == HTTPOk.status_code
                assert response.content_type == "application/javascript"

            async with session.get("http://localhost:8081/api/state.json") as response:
                assert response.status == HTTPOk.status_code
                json_content = await response.json()
                assert json_content == MOCK_DATA.model_dump()


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
async def test_html_page_data_updates() -> None:
    """Test that the API endpoint updates correctly when data changes."""
    async with (
        BackgroundStreamServer(host="localhost", port=8083) as server,
        ClientSession() as session,
    ):
        async with session.get("http://localhost:8083/api/state.json") as response:
            assert response.status == HTTPOk.status_code
            assert await response.json() is None

        server._current_data = MOCK_DATA

        async with session.get("http://localhost:8083/api/state.json") as response:
            assert response.status == HTTPOk.status_code
            json_content = await response.json()
            assert json_content == MOCK_DATA.model_dump()


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
    assert BackgroundStreamServer.get_instance() is None
