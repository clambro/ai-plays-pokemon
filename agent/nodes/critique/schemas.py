"""Data models for critique in the top-level agent graph."""

from pydantic import BaseModel


class CritiqueResponse(BaseModel):
    """The response from the critique prompt."""

    critique: str
