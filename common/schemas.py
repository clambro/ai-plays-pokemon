from pydantic import BaseModel


class Coords(BaseModel):
    """A 2D coordinate pair."""

    row: int
    col: int

    @property
    def y(self) -> int:
        """Alias for row."""
        return self.row

    @property
    def x(self) -> int:
        """Alias for col."""
        return self.col

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

    def __add__(self, other: "Coords") -> "Coords":
        """Add two coordinates together."""
        return Coords(row=self.row + other.row, col=self.col + other.col)

    def __sub__(self, other: "Coords") -> "Coords":
        """Subtract two coordinates."""
        return Coords(row=self.row - other.row, col=self.col - other.col)
