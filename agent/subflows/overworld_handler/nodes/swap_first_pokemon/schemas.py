from pydantic import BaseModel, Field


class SwapPokemonError(Exception):
    """An error that occurs when swapping a Pokemon."""


class SwapFirstPokemonResponse(BaseModel):
    """The response from the overworld swap first Pokemon prompt."""

    thoughts: str
    index: int = Field(ge=1, le=5)
