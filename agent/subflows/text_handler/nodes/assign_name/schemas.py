from pydantic import BaseModel, Field


class NameResponse(BaseModel):
    """The response to the get name prompt."""

    thoughts: str
    name: str = Field(pattern=r"^[A-Z ]{1,8}$")
