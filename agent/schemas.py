from pydantic import BaseModel


class NavigationArgs(BaseModel):
    """The arguments for the navigate tool."""

    row: int
    col: int

    def __str__(self) -> str:
        """The string representation of the navigation arguments."""
        return f"({self.row}, {self.col})"
