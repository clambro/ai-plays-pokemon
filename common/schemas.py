from typing import Any

from pydantic import BaseModel, model_serializer, model_validator


class Coords(BaseModel):
    """A 2D coordinate pair."""

    row: int
    col: int

    @model_serializer
    def _to_tuple(self) -> tuple[int, int]:
        """Serialize the coordinate pair to a hashable tuple to avoid errors."""
        return (self.row, self.col)

    @model_validator(mode="before")
    @classmethod
    def _from_tuple(cls, data: Any) -> Any:  # noqa: ANN401
        """Validate the coordinate pair from a tuple."""
        if isinstance(data, str):
            data = tuple(int(x) for x in data.strip("()").split(","))
        if isinstance(data, tuple) and len(data) == 2:  # noqa: PLR2004
            return {"row": data[0], "col": data[1]}
        return data

    @property
    def length(self) -> int:
        """Get the length in manhattan distance of the coordinate pair."""
        return abs(self.row) + abs(self.col)

    def __str__(self) -> str:
        return f"({self.row}, {self.col})"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        """Check if two coordinates are equal."""
        if not isinstance(other, Coords):
            return False
        return self.row == other.row and self.col == other.col

    def __hash__(self) -> int:
        """Hash the coordinate pair."""
        return hash((self.row, self.col))

    def __add__(self, other: "Coords | tuple[int, int]") -> "Coords":
        """Add two coordinates together."""
        if isinstance(other, Coords):
            return Coords(row=self.row + other.row, col=self.col + other.col)
        return Coords(row=self.row + other[0], col=self.col + other[1])

    def __sub__(self, other: "Coords | tuple[int, int]") -> "Coords":
        """Subtract two coordinates."""
        if isinstance(other, Coords):
            return Coords(row=self.row - other.row, col=self.col - other.col)
        return Coords(row=self.row - other[0], col=self.col - other[1])
