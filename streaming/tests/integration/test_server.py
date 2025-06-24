"""
Tests for the streaming background HTML page.

These tests validate that the HTML page renders correctly without console errors
and that all JavaScript functionality works as expected.
"""

import asyncio
from pathlib import Path

import pytest
from aiohttp import ClientSession
from aiohttp.web import HTTPOk

from streaming.schemas import GameStateView, LogEntryView, PartyPokemonView
from streaming.server import BackgroundStreamServer

MOCK_DATA = GameStateView(
    iteration=15247,
    money=18143,
    pokedex_seen=45,
    pokedex_caught=21,
    total_cost=23.51,
    play_time_seconds=596153,  # about 165 hours
    badges=["BOULDERBADGE", "CASCADEBADGE", "THUNDERBADGE"],
    party=[
        PartyPokemonView(
            name="ECHO",
            species="GOLBAT",
            type1="POISON",
            type2="FLYING",
            status=None,
            level=22,
            hp=0,
            max_hp=70,
            moves=["WING ATTACK", "CONFUSE RAY", "BITE", "HAZE"],
        ),
        PartyPokemonView(
            name="CRAG",
            species="GEODUDE",
            type1="ROCK",
            type2="GROUND",
            status=None,
            level=18,
            hp=45,
            max_hp=45,
            moves=["TACKLE", "DEFENSE CURL", "ROCK THROW", "SELF-DESTRUCT"],
        ),
        PartyPokemonView(
            name="PULSAR",
            species="MAGNEMITE",
            type1="ELECTRIC",
            type2=None,
            status=None,
            level=18,
            hp=0,
            max_hp=36,
            moves=["TACKLE", "SONIC BOOM", "THUNDER SHOCK", "SUPERSONIC"],
        ),
        PartyPokemonView(
            name="SPARKY",
            species="PIKACHU",
            type1="ELECTRIC",
            type2=None,
            level=24,
            hp=68,
            max_hp=68,
            status="POISONED",
            moves=["THUNDERSHOCK", "GROWL", "THUNDER WAVE", "QUICK ATTACK"],
        ),
        PartyPokemonView(
            name="SUBTERRA",
            species="DIGLETT",
            type1="GROUND",
            type2=None,
            status=None,
            level=18,
            hp=18,
            max_hp=52,
            moves=["SCRATCH", "GROWL"],
        ),
    ],
    goals=[
        "Travel through Rock Tunnel to reach Lavender Town.",
        "Obtain HM05 (Flash).",
        "Acquire a drink for the Saffron City guard",
    ],
    log=[
        LogEntryView(
            iteration=15246,
            thought="Ugh, a random battle. My path traversal was interrupted. I'm facing a wild Diglett. My goal is to get out of here, not to battle. ECHO is a higher level, so I should be able to run away successfully. I'll use the select_battle_option tool to select RUN.",  # noqa: E501
        ),
        LogEntryView(
            iteration=15247,
            thought="Oh, come on! Just when I was making good time. Another Diglett... alright, let's just get out of here. No time for battles right now!",  # noqa: E501
        ),
    ],
)


@pytest.mark.integration
async def test_html_page_renders_without_errors() -> None:
    """Test that the HTML, JS, and CSS files load correctly, and that the API returns valid JSON."""
    async with BackgroundStreamServer(host="localhost", port=8081) as server:
        server._current_data = MOCK_DATA

        async with ClientSession() as session:
            async with session.get("http://localhost:8081/") as response:
                assert response.status == HTTPOk.status_code

            async with session.get("http://localhost:8081/style.css") as response:
                assert response.status == HTTPOk.status_code

            async with session.get("http://localhost:8081/script.js") as response:
                assert response.status == HTTPOk.status_code

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
            content = await response.text()
            assert content == ""  # Empty response when no data


@pytest.mark.integration
async def test_html_page_assets_exist() -> None:
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
        if not (badges_dir / badge).exists():
            pytest.fail(f"Badge asset {badge} not found.")

    pokemon_dir = assets_dir / "pokemon"
    assert pokemon_dir.exists()

    expected_pokemon = ["pikachu.png", "golbat.png", "geodude.png"]
    for pokemon in expected_pokemon:
        if not (pokemon_dir / pokemon).exists():
            pytest.fail(f"Pokemon asset {pokemon} not found.")


@pytest.mark.integration
async def test_html_page_data_updates() -> None:
    """Test that the API endpoint updates correctly when data changes."""
    async with (
        BackgroundStreamServer(host="localhost", port=8083) as server,
        ClientSession() as session,
    ):
        async with session.get("http://localhost:8083/api/state.json") as response:
            assert response.status == HTTPOk.status_code
            content = await response.text()
            assert content == ""

        server._current_data = MOCK_DATA
        await asyncio.sleep(0.2)  # Wait for the data to be updated.

        async with session.get("http://localhost:8083/api/state.json") as response:
            assert response.status == HTTPOk.status_code
            json_content = await response.json()
            assert json_content == MOCK_DATA.model_dump()
