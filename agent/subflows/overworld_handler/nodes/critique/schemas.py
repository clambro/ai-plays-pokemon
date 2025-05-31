from pydantic import BaseModel


class CritiqueResponse(BaseModel):
    """The response from the critique prompt."""

    critique: str
