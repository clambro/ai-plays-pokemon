from pydantic import BaseModel, Field


class SummaryMemoryUpdate(BaseModel):
    """An update to the summary memory."""

    description: str
    importance: int = Field(ge=1, le=5)


class UpdateSummaryMemoryResponse(BaseModel):
    """Response to the update summary memory prompts."""

    memories: list[SummaryMemoryUpdate]
