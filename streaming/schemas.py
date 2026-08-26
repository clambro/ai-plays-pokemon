"""Messages exchanged with the background streaming client."""

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from agent.schemas import PublicLog
    from agent.state import AgentState
    from emulator.game_state import GameState


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
    def from_game_state(cls, game_state: GameState) -> list[PartyPokemonView]:
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
    def from_public_log(cls, public_log: PublicLog) -> list[LogEntryView]:
        """Create stream log entries from the dedicated public log."""
        return [
            cls(iteration=entry.iteration, thought=entry.content) for entry in public_log.entries
        ]


class GameStateView(BaseModel):
    """A view of the game state to be displayed in the background stream."""

    iteration: int
    money: int
    pokedex_seen: int
    pokedex_caught: int
    total_tokens: int
    total_cost: float
    play_time_seconds: int
    badges: list[str]
    party: list[PartyPokemonView]
    goals: list[str]
    log: list[LogEntryView]

    @classmethod
    def from_states(
        cls,
        agent_state: AgentState,
        game_state: GameState,
    ) -> GameStateView:
        """Create a view of the game state from the agent and game states."""
        pokemon = PartyPokemonView.from_game_state(game_state)
        log = LogEntryView.from_public_log(agent_state.public_log)
        return cls(
            iteration=agent_state.iteration,
            money=game_state.player.money,
            pokedex_seen=game_state.player.pokedex_seen,
            pokedex_caught=len(game_state.player.pokedex_caught),
            total_tokens=agent_state.total_tokens,
            total_cost=agent_state.total_cost,
            play_time_seconds=game_state.player.play_time_seconds,
            badges=[str(badge) for badge in game_state.player.badges],
            party=pokemon,
            goals=[goal.goal for goal in agent_state.goals.goals],
            log=log,
        )
