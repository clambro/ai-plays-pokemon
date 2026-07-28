"""Data models for retrieving long-term memory."""

from pydantic import BaseModel, Field

from common.constants import MAX_LONG_TERM_MEMORIES_RETRIEVED


class RetrieveLongTermMemoryResponse(BaseModel):
    """Long-term-memory titles selected for the current agent context."""

    titles: list[str] = Field(max_length=MAX_LONG_TERM_MEMORIES_RETRIEVED)
