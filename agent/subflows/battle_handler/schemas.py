from pydantic import BaseModel

from common.enums import PokeballItem


class FightToolArgs(BaseModel):
    """The arguments for the use move tool."""

    move_index: int
    move_name: str

    def to_string(self) -> str:
        """Convert the arguments to a string."""
        return f"Use {self.move_name}."


class SwitchPokemonToolArgs(BaseModel):
    """The arguments for the switch pokemon tool."""

    party_index: int
    name: str
    species: str

    def to_string(self) -> str:
        """Convert the arguments to a string."""
        return f"Switch to {self.name} ({self.species})."


class ThrowBallToolArgs(BaseModel):
    """The arguments for the throw ball tool."""

    item_index: int
    ball: PokeballItem

    def to_string(self) -> str:
        """Convert the arguments to a string."""
        return f"Throw a {self.ball}."


class RunToolArgs(BaseModel):
    """The arguments for the run tool."""

    def to_string(self) -> str:
        """Convert the arguments to a string."""
        return "Run."


BattleToolArgs = FightToolArgs | SwitchPokemonToolArgs | ThrowBallToolArgs | RunToolArgs
