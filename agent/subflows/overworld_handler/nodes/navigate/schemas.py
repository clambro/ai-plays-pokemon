from pydantic import BaseModel


class NavigationResponse(BaseModel):
    """The response from the overworld navigation prompt."""

    thoughts: str
    row: int
    col: int

    @property
    def coords(self) -> tuple[int, int]:
        """The coordinates of the tile to navigate to."""
        return self.row, self.col
