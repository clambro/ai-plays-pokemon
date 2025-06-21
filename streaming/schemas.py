from pydantic import BaseModel

from agent.state import AgentState
from database.llm_messages.repository import get_total_llm_cost
from emulator.game_state import YellowLegacyGameState


class PartyPokemonView(BaseModel):
    """A view of a Pokemon to be displayed in the background stream."""

    name: str
    species: str
    type1: str
    type2: str | None
    level: int
    hp: int
    max_hp: int
    status: str | None
    moves: list[str]

    @classmethod
    def from_game_state(cls, game_state: YellowLegacyGameState) -> list["PartyPokemonView"]:
        """Create a view of the Pokemon from the game state."""
        return [
            cls(
                name=pokemon.name,
                species=pokemon.species,
                type1=pokemon.type1,
                type2=pokemon.type2,
                level=pokemon.level,
                hp=pokemon.hp,
                max_hp=pokemon.max_hp,
                status=pokemon.status,
                moves=[move.name for move in pokemon.moves],
            )
            for pokemon in game_state.party
        ]


class LogEntryView(BaseModel):
    """A view of a log entry to be displayed in the background stream."""

    iteration: int
    thought: str

    @classmethod
    def from_agent_state(cls, state: AgentState) -> list["LogEntryView"]:
        """Create a view of the log entry from the agent state."""
        return [
            cls(
                iteration=piece.iteration,
                thought=piece.content,
            )
            for piece in state.raw_memory.pieces.values()
        ]


class GameStateView(BaseModel):
    """A view of the game state to be displayed in the background stream."""

    iteration: int
    money: int
    pokedex_seen: int
    pokedex_caught: int
    total_cost: float
    play_time_seconds: int
    badges: list[str]
    party: list[PartyPokemonView]
    goals: list[str]
    log: list[LogEntryView]

    @classmethod
    async def from_states(
        cls,
        agent_state: AgentState,
        game_state: YellowLegacyGameState,
    ) -> "GameStateView":
        """Create a view of the game state from the agent and game states."""
        pokemon = PartyPokemonView.from_game_state(game_state)
        log = LogEntryView.from_agent_state(agent_state)
        cost = await get_total_llm_cost()
        return cls(
            iteration=agent_state.iteration,
            money=game_state.player.money,
            pokedex_seen=game_state.player.pokedex_seen,
            pokedex_caught=game_state.player.pokedex_caught,
            total_cost=cost,
            play_time_seconds=game_state.player.play_time_seconds,
            badges=game_state.player.badges,
            party=pokemon,
            goals=agent_state.goals.goals,
            log=log,
        )
