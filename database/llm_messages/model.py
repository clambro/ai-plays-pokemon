import uuid
from datetime import datetime

from pydantic import UUID4
from sqlalchemy import UUID, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import SQLAlchemyBase


class LLMMessageDBModel(SQLAlchemyBase):
    """A table for LLM messages."""

    __tablename__ = "llm_message"

    id: Mapped[UUID4] = mapped_column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    model: Mapped[str] = mapped_column(String, nullable=False)
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    response: Mapped[str] = mapped_column(String, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    response_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
