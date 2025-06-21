"""
Hacky script to shove some dummy data into the background server and spin it up so that I can
quickly visualize styles and layouts.
"""

import asyncio

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
            species="Golbat",
            type1="POISON",
            type2="FLYING",
            status=None,
            level=22,
            hp=0,
            max_hp=70,
            moves=["Wing Attack", "Confuse Ray", "Bite", "Haze"],
        ),
        PartyPokemonView(
            name="CRAG",
            species="Geodude",
            type1="ROCK",
            type2="GROUND",
            status=None,
            level=18,
            hp=45,
            max_hp=45,
            moves=["Tackle", "Defense Curl", "Rock Throw", "Self-Destruct"],
        ),
        PartyPokemonView(
            name="PULSAR",
            species="Magnemite",
            type1="ELECTRIC",
            type2=None,
            status=None,
            level=18,
            hp=0,
            max_hp=36,
            moves=["Tackle", "Sonic Boom", "Thunder Shock", "Supersonic"],
        ),
        PartyPokemonView(
            name="SPARKY",
            species="Pikachu",
            type1="ELECTRIC",
            type2=None,
            level=24,
            hp=68,
            max_hp=68,
            status="POISONED",
            moves=["Thunder Shock", "Growl", "Thunder Wave", "Quick Attack"],
        ),
        PartyPokemonView(
            name="SUBTERRA",
            species="Diglett",
            type1="GROUND",
            type2=None,
            status=None,
            level=18,
            hp=18,
            max_hp=52,
            moves=["Scratch", "Growl"],
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


async def main() -> None:
    """Run the server with mock data for a few seconds."""
    async with BackgroundStreamServer() as server:
        server._current_data = MOCK_DATA  # noqa: SLF001
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
